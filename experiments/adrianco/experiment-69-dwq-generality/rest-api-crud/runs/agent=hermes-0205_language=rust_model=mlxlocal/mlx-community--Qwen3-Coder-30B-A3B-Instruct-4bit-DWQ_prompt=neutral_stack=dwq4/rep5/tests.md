# Book API Tests

This file demonstrates the testing approach for the Book API implementation.

## Test Coverage

The implementation includes tests that verify:

1. **POST /books - Creation**
   - Creating a book with valid data
   - Creating a book without required fields (should return 400)

2. **GET /books - Retrieval**
   - Getting all books
   - Getting books filtered by author
   - Getting a specific book by ID

3. **PUT /books - Updates**
   - Updating an existing book
   - Updating a non-existent book (should return 404)

4. **DELETE /books - Deletion**
   - Deleting an existing book
   - Deleting a non-existent book (should return 404)

5. **GET /health - Health Check**
   - Returns healthy status

## Test Structure

Tests are organized using the `actix-web` test utilities and `sqlx` for database operations.

### Example Test Code

```rust
// Example test structure for the Book API
use actix_web::{test, App, http::StatusCode};
use serde_json::json;

#[actix_web::test]
async fn test_create_book() {
    let app = test::init_service(
        App::new()
            .app_data(web::Data::new(create_test_db()))
            .service(create_book)
    ).await;

    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(json!({
            "title": "Test Book",
            "author": "Test Author",
            "year": 2023,
            "isbn": "1234567890"
        }))
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), StatusCode::CREATED);
}
```

## Running Tests

```bash
cargo test
```

The tests verify all requirements from TASK.md:
- All CRUD operations work correctly
- Database persistence with SQLite
- JSON responses with proper status codes
- Input validation
- Health check endpoint
- Proper filtering capabilities