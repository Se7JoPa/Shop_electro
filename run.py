"""Start the local server and open its page in the default browser."""
import argparse
import sys
import threading
import webbrowser
import sqlite3
from werkzeug.serving import make_server
from webapp import create_app


def main():
    parser = argparse.ArgumentParser(description='Магазин электроники в браузере')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--vertical', action='store_true', help='Открыть узкий вертикальный интерфейс')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('Порт должен быть от 1 до 65535.')
    try:
        app = create_app()
        server = make_server('127.0.0.1', args.port, app, threaded=True)
    except (OSError, ValueError, sqlite3.Error) as error:
        print('Не удалось запустить магазин:', error)
        return 1
    address = f'http://127.0.0.1:{args.port}' + ('/?view=vertical' if args.vertical else '')
    print(f'Магазин открыт: {address}\nДля остановки нажмите Ctrl+C. Не закрывайте терминал во время работы.')
    if not args.no_browser:
        timer = threading.Timer(.6, webbrowser.open, args=(address,))
        timer.daemon = True
        timer.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nМагазин остановлен.')
    finally:
        server.server_close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
