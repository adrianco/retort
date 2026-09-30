"""Run the API: python -m books_api [--host H] [--port P] [--db PATH]"""

import argparse
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from .app import create_app
from .store import BookStore


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--db", default="books.db", help="SQLite file path")
    args = p.parse_args()

    app = create_app(BookStore(args.db))
    with make_server(args.host, args.port, app, ThreadingWSGIServer, WSGIRequestHandler) as srv:
        print(f"Serving on http://{args.host}:{args.port} (db: {args.db})")
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
