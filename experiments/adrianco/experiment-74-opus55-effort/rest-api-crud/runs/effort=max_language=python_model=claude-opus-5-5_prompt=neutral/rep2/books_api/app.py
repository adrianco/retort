"""HTTP routes for the book collection, and the application factory."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response, status
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from books_api import __version__
from books_api.db import MAX_ID, BookRepository
from books_api.errors import Problem, install_error_handlers, problem_response
from books_api.schemas import Book, BookIn

DEFAULT_DB_PATH = "books.db"

#: Largest request body accepted. A book is well under 5 KB of JSON.
MAX_BODY_BYTES = 1024 * 1024

# Declaring a 4XX response also stops FastAPI from documenting its default 422,
# which this API never sends: validation failures are 400.
router = APIRouter(
    responses={
        "4XX": {"model": Problem, "description": "Client error (RFC 9457 problem details)"},
        503: {"model": Problem, "description": "The database cannot be used"},
    }
)


def get_repository(request: Request) -> BookRepository:
    return request.app.state.repository


Repository = Annotated[BookRepository, Depends(get_repository)]


def _book_not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "Book not found")


def parse_book_id(book_id: str) -> int:
    """Resolve the ``{book_id}`` path segment.

    A segment that cannot be the id of a stored book (``abc``, ``0``, ``-1``, a
    number beyond SQLite's 64-bit range) names no resource, so it is a 404 like
    any other unknown id rather than a validation error.
    """
    # Length is checked before int(): converting thousands of digits is slow,
    # and Python refuses outright past 4300 digits.
    if book_id.isascii() and book_id.isdigit() and len(book_id) <= len(str(MAX_ID)):
        value = int(book_id)
        if 0 < value <= MAX_ID:
            return value
    raise _book_not_found()


BookId = Annotated[int, Depends(parse_book_id)]


async def require_json(request: Request) -> None:
    """Answer 415 when a body arrives without a JSON Content-Type.

    FastAPI only parses bodies declared as JSON. Without this check, a client
    that forgets the header gets a misleading "must be a JSON object" error.
    """
    media_type = request.headers.get("content-type", "").partition(";")[0].strip().lower()
    maintype, _, subtype = media_type.partition("/")
    is_json = maintype == "application" and (subtype == "json" or subtype.endswith("+json"))
    if not is_json and await request.body():
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Content-Type must be application/json"
        )


@router.get("/health")
def health(repository: Repository) -> dict[str, str]:
    """Report whether the service is up and can read its database (503 if not)."""
    repository.ping()
    return {"status": "ok"}


@router.post(
    "/books", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_json)]
)
def create_book(
    book: BookIn, repository: Repository, request: Request, response: Response
) -> Book:
    """Add a book. The response holds the stored book, and its URL in ``Location``."""
    created = repository.create(book)
    # A relative URL: an absolute one is built from the Host header, which
    # could be malformed and fail here, after the book has been saved.
    path = request.app.url_path_for("get_book", book_id=str(created.id))
    response.headers["Location"] = request.scope.get("root_path", "") + path
    return created


@router.get("/books")
def list_books(repository: Repository, author: str | None = None) -> list[Book]:
    """List books in the order they were added.

    ``?author=`` keeps only books whose author contains the given text, ignoring case.
    """
    return repository.list_books(author=author.strip() if author else None)


@router.get("/books/{book_id}")
def get_book(book_id: BookId, repository: Repository) -> Book:
    book = repository.get(book_id)
    if book is None:
        raise _book_not_found()
    return book


@router.put("/books/{book_id}", dependencies=[Depends(require_json)])
def replace_book(book_id: BookId, book: BookIn, repository: Repository) -> Book:
    """Replace a book with the given representation.

    The body is validated exactly as for POST (title and author are required).
    Optional fields that are left out are cleared.
    """
    replaced = repository.replace(book_id, book)
    if replaced is None:
        raise _book_not_found()
    return replaced


@router.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: BookId, repository: Repository) -> Response:
    if not repository.delete(book_id):
        raise _book_not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


class BodySizeLimit:
    """ASGI middleware that answers 413 to request bodies over ``max_bytes``.

    A declared Content-Length is checked before anything is read, and a
    streamed (chunked) body is counted as it arrives, so an oversized body is
    never held in memory whole.
    """

    def __init__(self, app: ASGIApp, max_bytes: int = MAX_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes
        self.detail = f"Request body is larger than {max_bytes} bytes"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = dict(scope["headers"]).get(b"content-length", b"")
        # More than 18 digits is too large for certain, and keeps int() cheap.
        if declared.isdigit() and (len(declared) > 18 or int(declared) > self.max_bytes):
            response = problem_response(status.HTTP_413_CONTENT_TOO_LARGE, self.detail)
            await response(scope, receive, send)
            return
        received = 0

        async def receive_within_limit() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    # FastAPI re-raises HTTPExceptions from reading the body,
                    # so this reaches the usual error handler.
                    raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, self.detail)
            return message

        await self.app(scope, receive_within_limit, send)


def create_app(db_path: str | Path | None = None) -> FastAPI:
    """Build the application.

    Books are stored in ``db_path``, else ``$BOOKS_API_DB``, else ``./books.db``.
    """
    repository = BookRepository(db_path or os.environ.get("BOOKS_API_DB") or DEFAULT_DB_PATH)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Fail at startup, not on the first request, if the file is unusable.
        repository.initialize()
        yield

    app = FastAPI(
        title="Books API",
        version=__version__,
        description="Manage a book collection.",
        lifespan=lifespan,
    )
    app.state.repository = repository
    install_error_handlers(app)
    app.add_middleware(BodySizeLimit)
    app.include_router(router)
    return app


#: For ASGI servers, e.g. ``uvicorn books_api.app:app``.
app = create_app()
