import configparser

from grice.db_controller import DBController
from grice.db_service import DBService
from grice.column_encoder import ColumnEncoder
from grice.errors import ConfigurationError
from flask import Flask, send_from_directory, render_template


def _print_start_screen():
    print("                               u")
    print("    .                       u$$$$")
    print("   $$$$$$bu.             u$$$$$$$$")
    print("  9$$$$$$$$$$R$       z$$$$$$$$$$$k")
    print(" '$$$$$$$$$$!$        $X$$$$$$$$$$$")
    print(" 8$$$$$$$$MM!E    .u  'B!MM$$$$$$$$>")
    print(" $$$$$$$$MMMXE .d$#$k  $!MM$$$$$$$$E")
    print("'$$$$$$$8MWHX$  9WXX$ dRXXSM8$$$$$$E")
    print(" $$$$$$$$$$$$$$$@@$~tW@WWWWeeWeWWee")
    print(" 4$$$$$$MMHX!!!!!9F  4$!!HMM8$$$$$F")
    print("  R$$$$$$MMMX!!!!Xk   9B!MMN$$$$$$")
    print("   #$$$$$$MMMMHH!!&   '$MMM$$$$$$~")
    print('    `$$$$$$$8MMMM!$>   4$M$$$$$$"')
    print("      ^*$$$$$$$8MMX$   '$$$$$$$")
    print('         ^#R$$$$$$$$$i  $$$$$"')
    print('                        $$$"')


def static_assets(path):
    return send_from_directory('../assets', path)

static_assets.methods = ['GET']


def index():
    return render_template('index.html')


class App:
    def __init__(self, config_path='./config.ini', use_waitress=True):
        _print_start_screen()
        config = configparser.ConfigParser()
        config.read(config_path)
        self._init_setup(config['server'])
        if use_waitress:
            self._init_waitress(config['server'])
        self._init_flask_app()
        self._db_service = DBService(config['database'])
        self._db_controller = DBController(self.flask_app, self._db_service)

    def _init_setup(self, server_config):
        self.debug = server_config.getboolean('debug', False)

        try:
            self.secret = server_config['secret']
        except KeyError:
            raise ConfigurationError('Entry "secret" required in section "server"')

    def _init_waitress(self, server_config):
        self.host = server_config.get('host', '0.0.0.0')
        self.port = server_config.getint('port', 8080)
        self.threads = server_config.getint('threads', 8)

    def _init_flask_app(self):
        self.flask_app = Flask('grice')
        self.flask_app.debug = self.debug
        self.flask_app.secret_key = self.secret
        self.flask_app.json_encoder = ColumnEncoder
        self.flask_app.add_url_rule('/', 'index', index)
        self.flask_app.add_url_rule('/assets/<path:path>', 'assets', static_assets)

    def serve(self):
        from waitress import serve
        self.flask_app.logger.info('Starting server...')
        serve(self.flask_app, host=self.host, port=self.port, threads=self.threads)
