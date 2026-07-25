# Book API

A simple REST API for managing a book collection written in TypeScript.

## Setup

```bash
npm install
```

## Build

```bash
npm run build
```

## Run

```bash
npm start
```

The server will listen on port **3000** by default.

## Development

```bash
npm run dev
```

## Tests

```bash
npm test
```

## Endpoints

- **GET /health** – health check
- **POST /books** – create a book
- **GET /books** – list all books (optional `?author=` filter)
- **GET /books/:id** – get a book
- **PUT /books/:id** – update a book
- **DELETE /books/:id** – delete a book

The data is stored in an SQLite database in `data/books.db`.
