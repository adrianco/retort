# Book collection API

Run `python3 app.py` from this directory with Python 3.9 or newer.
The service uses Python's standard-library WSGI server and SQLite. No packages
need to be installed. It listens on http://127.0.0.1:8000 and creates
`books.sqlite3` in the current directory. Set `PORT` and `BOOKS_DB` to change
the port and database file. Run the tests with `python3 -m unittest -v`.

| Method and path | Result |
| --- | --- |
| POST /books | Create a book and return it with status 201 and a Location header |
| GET /books | Return books in ID order |
| GET /books?author=Jane%20Austen | Return exact, case-sensitive author matches |
| GET /books/{id} | Return one book |
| PUT /books/{id} | Replace a book and return its updated fields |
| DELETE /books/{id} | Delete a book and return JSON confirmation |
| GET /health | Check database availability and return service status |

Send JSON objects with nonblank strings for title and author. The optional year
is an integer and isbn is a string to preserve leading zeros. Omitted optional
fields become null on creation or replacement. Invalid book data returns 400,
an unsupported request media type returns 415, and missing books return 404.

```sh
curl -i http://127.0.0.1:8000/books -H 'Content-Type: application/json' \
  -d '{"title":"Emma","author":"Jane Austen","year":1815}'
```
