import configparser

from grice.db_controller import DBController
from grice.db_service import DBService
from grice.column_encoder import ColumnEncoder
from grice.errors import ConfigurationError
from flask import Flask, send_from_directory, render_template


def _print_start_screen0():
    print("                                  ..,cdk0XNNNNKx;.          ")
    print("                             ..,cdkO0KXXXXXNNNWWXkl'        ")
    print("                          .;ok0KXXXXXKKKKKKKXXXNNWWXx;.     ")
    print("                      .':dOKXKXKKXXKKKK000KKKXXXXNNNWXx,  ..")
    print("                 .,:ldOKXXKKKKKKKKKK00OO00KKKKKKKKXXXKOo:;c:")
    print("              .;dOKKKKK00KK000000000OOOOOOO0000000000Od,..,.")
    print("            .;dO0000000OOO00OOOOOOOOkkkxkkkkkkkkkkkkkxl.  .'")
    print("          .:dOOOOOOO0OOOOkkkkkkkkxxxxddddxdxxkkxxxxdol'     ")
    print("        .;xkkxkkkkkkkkkkxddddddddddddoccoddxxxxkxdol:.      ")
    print("       .o0Okxxxxxxxxxxxxdolllllllllllc;;:oodxxxxxoc;.       ")
    print("      ;OXX0kxdxxdoooddxxxoc;;::::::::;;,,:lodddddo:.        ")
    print("  .,cxKXXXX0kxxxdl::lodddl:;'''''....... .,loodxxxc.        ")
    print(".,lkKXKXXXK0Okxxdl;;cloool:.              .;odxxkko'        ")
    print("...;dxoooddddxxxoc,,:loolc,.               .cdxxxdc.        ")
    print("   .:oc:clodddddl,. 'loocc'                .:ddol;.         ")
    print("   .:ooodxxxxxo:'   .cdo::;.               ;ddoc;.          ")
    print("   'lodoooddl;.     'odo,''               :xxdl:,.          ")
    print("  .coolc::,..       ,lc;..               ;oooc;,.           ")
    print("  .',,'..          .:;.                .:l:;,..             ")
    print("                   ..                 .;l:..                ")


def _print_start_screen():
    print("................................................+77777777777777.................")
    print("...........................................7777III7II7II77I77777  ..............")
    print("........................................777IIIIIIIIIII7IIIII77777777............")
    print(".....................................77II7IIIIIIIIIIII?IIIII77I7777777..........")
    print("...................................7IIIIIIIIIIIIIII???I?III77II7I777777I........")
    print("................................77?IIIII7IIIIIIIIII??I?IIIIIIIIII77777I77.....?,")
    print("............................77IIIIIII7I?I?IIII?II????IIIIIIIIIIIIIIIIII?+??I++=.")
    print(".......................I7IIIIIIIIII?II?II?I?III??I???I????II??III?II???+~..==+..")
    print(".....................IIIIIIII?IIIII?I?????I???????????+??????????II????=?....=..")
    print("...................7??III?I?I???I???I???I??????+??+++?++??I????????????+?....=..")
    print("..................I?I+??????????????I?????????????+++++??+????+?????++++.....+?.")
    print("................7II????+??I??I+???+?????+?+??+?+++++++=++?++?+?+?++++==+........")
    print("..............+I??++???????I?I??+?+??++?+++++++++==~?++++???+++?+=+====.........")
    print(".............7??++++?++?++++??I++++++=+++++++=+=+==~=++++++++?++++==~=..........")
    print("............II?+++?+++++++++++=++===+++====+==++=~~:~=+=++++?+?++==~+...........")
    print("...........II??++++++++??+++++++++=~~============~~~:==+=++?+++++~==............")
    print("..........7III?+++++++=+=++++++?+++~~~~==~~~~~==~~~~:~===+++++++~==.............")
    print("........+IIII7I?+++++++=~====+++++=~~~::::~~~~~:~~::::~==+++++++=+..............")
    print("......7I77I777III+++?++=~~~===+++=~~~::::::::::,.......~=====++?=+,.............")
    print("...?III77II777III?+++++=::~~==+====~~...................===+?++??+?.............")
    print(".I==I77IIII77IIII??+++++~::=~=====~~....................~~=++++??=+.............")
    print("=..~~=?+=IIII???++++++=~:::===++==~=.....................==++?++??=.............")
    print("......?+~~:.:~~===++++=~~:.======~~+......................==++++=~=.............")
    print("......+==~:=~==+++++++==...=~=++=~~~......................==+++=~:..............")
    print("......+===+==++??+++===.....~=+==:=?.....................++++===:...............")
    print("......====++?++?++++=~......==++~:~+.....................+++==~~=...............")
    print(".....+=+++++?+++++=~........++++~,:=~...................+?+++=~~................")
    print(".....==+++==~+++==.........,==++,,,~...................????+=~~=................")
    print("....=+?~+====~~=...........~==+=::,...................++++++~~:~................")
    print("...??+++~=~~=..............==~:=.....................?+=~==::::.................")
    print("....::,~=.................===~......................++=~~~:,:...................")
    print("...................................................+++=.~.......................")
    print(".....................................................,..........................")


def static_assets(path):
    return send_from_directory('../assets', path)

static_assets.methods = ['GET']


def index():
    return render_template('index.html')


class App:
    def __init__(self, config_path='./config.ini', use_waitress=True, url=None):
        _print_start_screen()
        config = configparser.ConfigParser()
        config.read(config_path)
        self._init_setup(config['server'])
        if use_waitress:
            self._init_waitress(config['server'])
        self._init_flask_app()
        self._db_service = DBService(config['database'], url=url)
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
