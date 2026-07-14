# Book API

A REST API for managing a book collection using TypeScript, Express, and SQLite.

## Requirements
- Node.js (v14 or higher)
- npm

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd book-api
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

## Setup

1. Initialize the database:
   ```bash
   npm start
   ```
   The server will start and create the database file `books.db`.

## Running the Application

Start the server:
```bash
npm start
```

The server will run on port 3000 by default. You can change the port by setting the `PORT` environment variable.

## API Endpoints

### Health Check
- **GET** `/health`
  - Returns a health check response.

### Books
- **POST** `/books`
  - Creates a new book.
  - Request body: `{ "title": "string", "author": "string", "year": number, "isbn": "string" }`
  - Response: Created book with ID.

- **GET** `/books`
  - Returns a list of all books.
  - Query parameters:
    - `author`: Filter by author (optional).

- **GET** `/books/:id`
  - Returns a single book by ID.

- **PUT** `/books/:id`
  - Updates a book by ID.
  - Request body: Fields to update (e.g., `{ "title": "string" }`).
  - Response: Updated book.

- **DELETE** `/books/:id`
  - Deletes a book by ID.

## Running Tests

Run the tests with:
```bash
npm test
```

## Project Structure

- `src/`: Source code directory
  - `index.ts`: Main application file
  - `database.ts`: Database module
- `tests/`: Test files
  - `database.test.ts`: Database operations tests
  - `api.test.ts`: API endpoints tests
- `tsconfig.json`: TypeScript configuration
- `package.json`: Project dependencies and scripts

## Dependencies

- Express: Web framework for Node.js
- Body-parser: Middleware for parsing request bodies
- SQLite3: SQLite database driver
- TypeScript: Language for application development
- Mocha: Testing framework
- Chai: Assertion library for tests
- Supertest: Library for testing HTTP endpoints

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -m 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Open a pull request

## License

MIT License
