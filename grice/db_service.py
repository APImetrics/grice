from collections import namedtuple

from sqlalchemy.sql import Select

from grice.errors import ConfigurationError, NotFoundError
from sqlalchemy import create_engine, MetaData, Column, Table, select, not_, or_, asc, desc, and_
from sqlalchemy import engine
from sqlalchemy.engine import reflection

DEFAULT_PAGE = 0
DEFAULT_PER_PAGE = 50
FILTER_TYPES = ['lt', 'lte', 'eq', 'neq', 'gt', 'gte', 'in', 'not_in', 'bt', 'nbt']
LIST_FILTERS = ['in', 'not_in', 'bt', 'nbt']
SORT_DIRECTIONS = ['asc', 'desc']


def init_database(db_config):
    try:
        db_args = {
            'username': db_config['username'],
            'password': db_config['password'],
            'host': db_config['host'],
            'port': db_config['port'],
            'database': db_config['database']
        }
    except KeyError:
        msg = '"username", "password", "host", "port", and "database" are required fields of database config'
        raise ConfigurationError(msg)

    eng_url = engine.url.URL('postgresql', **db_args)

    return create_engine(eng_url)


def column_to_dict(column: Column):
    foreign_keys = []

    for fk in column.foreign_keys:
        fk_column = fk.column
        foreign_keys.append({'name': fk_column.name, 'table_name': fk_column.table.name})

    data = {
        'name': column.name,
        'primary_key': column.primary_key,
        'nullable': column.nullable,
        'type': column.type.__class__.__name__,
        'foreign_keys': foreign_keys,
        'table': column.table.name
    }

    return data


def table_to_dict(table: Table):
    return {
        'name': table.name,
        'schema': table.schema,
        'columns': [column_to_dict(column) for column in table.columns]
    }


def names_to_columns(column_names, table_columns, all_tables=None):
    columns = []

    for column_name in column_names:
        if all_tables:
            # this means we need to look up fully qualified column names.
            try:
                table_name, column_name = [value.strip() for value in column_name.split('.')]
                column = all_tables.get(table_name, Table()).columns.get(column_name, None)
            except ValueError:
                # If the column name doesn't have a '.' in it then it's not valid.
                column = None
        else:
            # This means we only need to look at the table_columns.
            column = table_columns.get(column_name)

        if column is not None:
            columns.append(column)

    return columns


def convert_url_value(url_value: str, column: Column):
    """
    Converts a given string value to the given Column's type.
    :param url_value: a string
    :param column: a sqlalchemy Column object
    :return: value converted to type in column object.
    """
    if column.type.python_type == bool:
        return url_value.lower() == 'true'
    else:
        return column.type.python_type(url_value)


class ColumnFilter:
    def __init__(self, column_name, filter_type, value=None, url_value=None, column: Column=None):
        """
        ColumnFilter will be used to apply filters to a column when using the table query API. They are parsed from the
        url via db_controller.parse_filters.

        :param column_name: The name of the column to filter
        :param filter_type: The type of filter to apply, must one of FILTER_TYPES.
        :param value: The value to apply with the filter type converted to the appropriate type via the column object.
        :param url_value: The value that came from the URL
        :param column: The SQLAlchemy Column object from the table.
        :return:
        """
        if filter_type not in FILTER_TYPES:
            raise ValueError('Invalid filter type "{}", valid types: {}'.format(filter_type, FILTER_TYPES))

        self.column_name = column_name
        self.filter_type = filter_type
        self.value = value
        self.url_value = url_value
        self._column = column

        if self._column is not None and self.url_value is not None:
            self.value = convert_url_value(url_value, self.column)

    @property
    def column(self):
        return self._column

    @column.setter
    def column(self, column):
        try:
            if self.url_value is not None:
                if self.filter_type in LIST_FILTERS:
                    values = []

                    for value in self.url_value.split(';'):
                        values.append(convert_url_value(value, column))

                    self.value = values
                else:
                    self.value = convert_url_value(self.url_value, column)
        except (ValueError, TypeError):
            raise(ValueError('Invalid value "{}" for type "{}"'.format(self.url_value, column.type.python_type)))

        self._column = column


def get_filter_expression(column: Column, column_filter: ColumnFilter):
    """
    Given a Column and ColumnFilter return an expression to use as a filter.
    :param column: sqlalchemy Column object
    :param column_filter: ColumnFilter object
    :return: sqlalchemy expression object
    """
    try:
        column_filter.column = column
    except ValueError:
        # Ignore bad filters.
        return None

    value = column_filter.value
    filter_type = column_filter.filter_type

    if filter_type == 'lt':
        return column < value
    elif filter_type == 'lte':
        return column <= value
    elif filter_type == 'eq':
        return column == value
    elif filter_type == 'neq':
        return column != value
    elif filter_type == 'gt':
        return column > value
    elif filter_type == 'gte':
        return column >= value
    elif filter_type == 'in':
        return column.in_(value)
    elif filter_type == 'not_in':
        return not_(column.in_(value))
    elif filter_type == 'bt':
        return column.between(*value)
    elif filter_type == 'nbt':
        return not_(column.between(*value))

    return None


def get_filter_expressions(column, filter_list: list):
    """
    Given a Column and a list of ColumnFilters return a filter expression.

    :param column: sqlalchemy Column
    :param filter_list: a list of ColumnFilter objects
    :return: list of sqlalchemy expression objects
    """
    expressions = []

    for column_filter in filter_list:
        expr = get_filter_expression(column, column_filter)

        if expr is not None:
            expressions.append(expr)

    return expressions


def apply_column_filters(table: Table, query, filters: dict):
    """
    Apply the ColumnFilters from the filters object to the query.

    - Goals is to be smart when applying filters.
        - multiple filters on a column should probably be OR'ed.
        - if lt value is smaller than gt value then we probably want to OR (i.e. lt 60 OR gt 120)
        - if lt value is bigger than gt value then we probably want to AND (i.e. lt 120 AND gt 60)
        - alternatively allow BETWEEN and NOT BETWEEN, and if multiples just OR those.
        - Filter sets between columns should be AND'ed.

    :param table: SQLAlchemy Table object.
    :param query: SQLAlchemy Select object.
    :param filters: The filters dict from db_controller.parse_filters: in form of column_name -> filters list
    :return:
    """

    for column_name, filter_list in filters.items():
        column = table.columns.get(column_name)

        if column is not None:
            filter_expressions = get_filter_expressions(column, filter_list)
            number_of_filters = len(filter_expressions)

            if number_of_filters == 0:
                # No valid filters for this column, so just continue.
                continue
            if number_of_filters == 1:
                # If we only have one filter then just put it in a where clause.
                query = query.where(filter_expressions[0])
            else:
                # If we have more than one filter then OR all filters
                query = query.where(or_(filter_expressions))

    return query


ColumnSort = namedtuple('ColumnSort', ['column_name', 'direction'])


def apply_column_sorts(table: Table, query, sorts: dict):
    for sort in sorts:
        if sort.column_name in table.columns:
            if sort.direction == 'asc':
                query = query.order_by(asc(table.columns.get(sort.column_name)))

            if sort.direction == 'desc':
                query = query.order_by(desc(table.columns.get(sort.column_name)))

    return query


ColumnPair = namedtuple('ColumnPair', ['from_column', 'to_column'])
TableJoin = namedtuple('TableJoin', ['table_name', 'column_pairs', 'outer_join'])


def apply_join(query: Select, tables: dict, table: Table, join: TableJoin):
    # TODO: enable multiple joins
    join_table = tables.get(join.table_name)

    if join_table is None:
        raise ValueError('Invalid join. Table with name "{}" does not exist.'.format(join.table_name))

    error_msg = 'Invalid join, "{}" is not a column on table "{}"'
    join_conditions = []

    for column_pair in join.column_pairs:
        from_col = table.columns.get(column_pair.from_column)
        to_col = join_table.columns.get(column_pair.to_column)

        if from_col is None:
            raise ValueError(error_msg.format(column_pair.from_column, table.name))

        if to_col is None:
            raise ValueError(error_msg.format(column_pair.to_column, join_table.name))

        join_conditions.append(from_col == to_col)

    return query.select_from(table.join(join_table, onclause=and_(*join_conditions), isouter=join.outer_join))


class DBService:
    """
    TODO:
        - Add methods for saving table queries
    """
    def __init__(self, db_config):
        self.meta = MetaData()
        self.db = init_database(db_config)
        self._reflect_database()

    def _reflect_database(self):
        """
        This method reflects the database and also instantiates an Inspector.
        :return:
        """
        self.meta.reflect(bind=self.db)
        self.inspector = reflection.Inspector.from_engine(self.db)

    def get_tables(self):
        schemas = {}

        for table in self.meta.sorted_tables:
            schema = table.schema

            if schema not in schemas:
                schemas[schema] = {}

            schemas[schema][table.name] = table_to_dict(table)

        return schemas

    def get_table(self, table_name):
        table = self.meta.tables.get(table_name, None)

        if table is None:
            raise NotFoundError('table "{}" does exist'.format(table_name))

        return table_to_dict(table)

    def query_table(self, table_name, column_names: set=None, page: int=DEFAULT_PAGE, per_page: int=DEFAULT_PER_PAGE,
                    filters: dict=None, sorts: dict=None, join: TableJoin=None):
        table = self.meta.tables.get(table_name, None)
        rows = []

        if column_names is None:
            columns = table.columns
        else:
            columns = names_to_columns(column_names, table.columns, all_tables=self.meta.tables)

        if len(columns) == 0:
            return []

        query = select(columns)

        if per_page > -1:
            query = query.limit(per_page).offset(page * per_page)

        if filters is not None:
            query = apply_column_filters(table, query, filters)

        if sorts is not None:
            query = apply_column_sorts(table, query, sorts)

        if join is not None:
            query = apply_join(query, self.meta.tables, table, join)

        with self.db.connect() as conn:
            result = conn.execute(query)

            for row in result:
                data = {}

                for column in columns:
                    full_column_name = column.table.name + '.' + column.name
                    data[full_column_name] = row[column]

                rows.append(data)

        column_data = [column_to_dict(column) for column in columns]

        return rows, column_data

if __name__ == '__main__':
    import configparser
    config = configparser.ConfigParser()
    config.read('../config.ini')
    s = DBService(config['database'])
    t = s.meta.tables.get('countrylanguage')
    cols = t.columns
    print(cols)
    # r = s.query_table('device_args', {'name', 'device_id'})
