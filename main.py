import argparse
import falcon

from wsgiref.simple_server import make_server
from TemplateLoaders import loader


MESSAGE_REQUEST_NOT_MATCHES = f'request not matches'
DEFAULT_TEMPLATE_DIRECTORY = 'templates'
DEFAULT_HOST = ''
DEFAULT_PORT = 5000

parser = argparse.ArgumentParser(
    prog='Emulator',
    description='Emulation API Handlers',
)

parser.add_argument('-t', '--template', dest='template', default=DEFAULT_TEMPLATE_DIRECTORY)
parser.add_argument('--placeholders', dest='placeholders', default=None, help='path to placeholders.json file')
parser.add_argument('-p', '--port', dest='port',type=int, default=DEFAULT_PORT)
parser.add_argument( '--host', dest='host', default=DEFAULT_HOST)

app = falcon.App()

if __name__ == '__main__':
    args = parser.parse_args()

    handlers = loader.load_templates(args.template, args.placeholders)

    for handler in handlers:
        app.add_route(handler.path, handler)
    print(f'Start ApiMock on {args.host}:{args.port}')
    try:
        with make_server(args.host, args.port, app) as httpd:
            httpd.serve_forever()
    except Exception as ex:
        exit(ex)
