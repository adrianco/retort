"""Book collection REST API built on the Python standard library."""
import json
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from src.db import BookRepository
from src.validation import ValidationError, validate_book

BOOK_ID_RE = re.compile(r"^/books/(\d+)/?$")
MAX_BODY = 1 << 20  # 1 MiB


def make_handler(repo: BookRepository):
    class BookHandler(BaseHTTPRequestHandler):
        server_version = "BookAPI/1.0"

        # ---- helpers -------------------------------------------------
        def _send(self, status: int, body=None) -> None:
            data = b"" if body is None else json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if data:
                self.wfile.write(data)

        def _error(self, status: int, message: str, details=None) -> None:
            body = {"error": message}
            if details:
                body["details"] = details
            self._send(status, body)

        def _read_json(self):
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "body too large")
                return None
            raw = self.rfile.read(length) if length else b""
            try:
                return json.loads(raw or b"null")
            except json.JSONDecodeError:
                self._error(HTTPStatus.BAD_REQUEST, "invalid JSON body")
                return None

        def _validated_body(self):
            payload = self._read_json()
            if payload is None and not self._headers_sent_error():
                self._error(HTTPStatus.BAD_REQUEST, "request body required")
                return None
            if payload is None:
                return None
            try:
                return validate_book(payload)
            except ValidationError as exc:
                self._error(HTTPStatus.UNPROCESSABLE_CONTENT, "validation failed", exc.errors)
                return None

        def _headers_sent_error(self) -> bool:
            # BaseHTTPRequestHandler sets _headers_buffer only during send; use a flag instead.
            return getattr(self, "_responded", False)

        def send_response(self, code, message=None):
            self._responded = True
            super().send_response(code, message)

        def log_message(self, fmt, *args):  # quieter default logging
            if getattr(self.server, "quiet", False):
                return
            super().log_message(fmt, *args)

        # ---- routing -------------------------------------------------
        def do_GET(self):
            url = urlparse(self.path)
            if url.path in ("/health", "/health/"):
                return self._send(HTTPStatus.OK, {"status": "ok"})
            if url.path in ("/books", "/books/"):
                qs = parse_qs(url.query)
                author = qs.get("author", [None])[0]
                return self._send(HTTPStatus.OK, repo.list(author=author))
            m = BOOK_ID_RE.match(url.path)
            if m:
                book = repo.get(int(m.group(1)))
                if book is None:
                    return self._error(HTTPStatus.NOT_FOUND, "book not found")
                return self._send(HTTPStatus.OK, book)
            return self._error(HTTPStatus.NOT_FOUND, "route not found")

        def do_POST(self):
            url = urlparse(self.path)
            if url.path not in ("/books", "/books/"):
                return self._error(HTTPStatus.NOT_FOUND, "route not found")
            data = self._validated_body()
            if data is None:
                return None
            book = repo.create(**data)
            return self._send(HTTPStatus.CREATED, book)

        def do_PUT(self):
            url = urlparse(self.path)
            m = BOOK_ID_RE.match(url.path)
            if not m:
                return self._error(HTTPStatus.NOT_FOUND, "route not found")
            data = self._validated_body()
            if data is None:
                return None
            book = repo.update(int(m.group(1)), **data)
            if book is None:
                return self._error(HTTPStatus.NOT_FOUND, "book not found")
            return self._send(HTTPStatus.OK, book)

        def do_DELETE(self):
            url = urlparse(self.path)
            m = BOOK_ID_RE.match(url.path)
            if not m:
                return self._error(HTTPStatus.NOT_FOUND, "route not found")
            if not repo.delete(int(m.group(1))):
                return self._error(HTTPStatus.NOT_FOUND, "book not found")
            return self._send(HTTPStatus.NO_CONTENT)

    return BookHandler


def create_server(db_path: str = "books.db", host: str = "127.0.0.1",
                  port: int = 8000, quiet: bool = False) -> ThreadingHTTPServer:
    repo = BookRepository(db_path)
    server = ThreadingHTTPServer((host, port), make_handler(repo))
    server.repo = repo  # type: ignore[attr-defined]
    server.quiet = quiet  # type: ignore[attr-defined]
    return server


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Book collection REST API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", default="books.db")
    args = parser.parse_args()
    server = create_server(args.db, args.host, args.port)
    print(f"Serving on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
