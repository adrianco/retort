use axum::{
    extract::Path,
    http::StatusCode,
    response::Json,
    routing::{delete, get, post, put},
    Router,
};
use std::sync::Arc;
use tokio::sync::Mutex;

use crate::{
    database::{create_book, delete_book, get_all_books, get_book_by_id, update_book},
    models::{AppError, Book, BookInput, BookUpdate},
};

mod database;
mod models;

async fn health() -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "ok",
    }))
}

async fn list_books(
    pool: axum::extract::State<crate::database::DbPool>,
    author: Option<String>,
) -> Result<Json<Vec<Book>>, AppError> {
    let books = get_all_books(&pool, author).await?;
    Ok(Json(books))
}

async fn get_book(
    pool: axum::extract::State<crate::database::DbPool>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, AppError> {
    let book = get_book_by_id(&pool, id).await?;
    Ok(Json(book))
}

async fn create_book_handler(
    pool: axum::extract::State<crate::database::DbPool>,
    Json(input): Json<BookInput>,
) -> Result<(StatusCode, Json<Book>), AppError> {
    let book = create_book(&pool, input).await?;
    Ok((StatusCode::CREATED, Json(book)))
}

async fn update_book_handler(
    pool: axum::extract::State<crate::database::DbPool>,
    Path(id): Path<i64>,
    Json(update): Json<BookUpdate>,
) -> Result<Json<Book>, AppError> {
    let book = update_book(&pool, id, update).await?;
    Ok(Json(book))
}

async fn delete_book_handler(
    pool: axum::extract::State<crate::database::DbPool>,
    Path(id): Path<i64>,
) -> Result<StatusCode, AppError> {
    delete_book(&pool, id).await?;
    Ok(StatusCode::NO_CONTENT)
}

#[tokio::main]
async fn main() {
    let pool = crate::database::init_db("books.db")
        .await
        .expect("Failed to initialize database");

    let app = Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book_handler).get(list_books))
        .route("/books/{id}", put(update_book_handler).delete(delete_book_handler))
        .route("/books/{id}", get(get_book))
        .with_state(pool);

    let listener = tokio::net::TcpListener::bind("127.0.0.1:3000")
        .await
        .unwrap();
    println!("Server running on http://127.0.0.1:3000");
    axum::serve(listener, app).await.unwrap();
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::http::StatusCode;
    use axum_test::TestServer;
    use serde_json::json;

    #[tokio::test]
    async fn test_health_endpoint() {
        let pool = crate::database::init_db(":memory:").await.unwrap();
        let app = Router::new()
            .route("/health", get(health))
            .with_state(pool);

        let server = TestServer::new(app).unwrap();
        let response = server.get("/health").await;
        response.assert_status(StatusCode::OK);
        response.assert_json(&json!({"status": "ok"}));
    }

    #[tokio::test]
    async fn test_create_book() {
        let pool = crate::database::init_db(":memory:").await.unwrap();
        let app = Router::new()
            .route("/books", post(create_book_handler))
            .with_state(pool);

        let server = TestServer::new(app).unwrap();
        let response = server
            .post("/books")
            .json(&json!({
                "title": "Test Book",
                "author": "Test Author",
                "year": 2024,
                "isbn": "1234567890"
            }))
            .await;
        
        response.assert_status(StatusCode::CREATED);
        let body = response.json::<serde_json::Value>();
        assert_eq!(body["title"], "Test Book");
        assert_eq!(body["author"], "Test Author");
    }

    #[tokio::test]
    async fn test_create_book_validation() {
        let pool = crate::database::init_db(":memory:").await.unwrap();
        let app = Router::new()
            .route("/books", post(create_book_handler))
            .with_state(pool);

        let server = TestServer::new(app).unwrap();
        
        // Test missing title
        let response = server
            .post("/books")
            .json(&json!({
                "author": "Test Author",
                "year": 2024,
                "isbn": "1234567890"
            }))
            .await;
        response.assert_status(StatusCode::UNPROCESSABLE_ENTITY);
        
        // Test missing author
        let response = server
            .post("/books")
            .json(&json!({
                "title": "Test Book",
                "year": 2024,
                "isbn": "1234567890"
            }))
            .await;
        response.assert_status(StatusCode::UNPROCESSABLE_ENTITY);
    }

    #[tokio::test]
    async fn test_get_all_books_with_author_filter() {
        let pool = crate::database::init_db(":memory:").await.unwrap();
        
        // Insert some books directly into the database using the same pool
        sqlx::query(
            r#"
            INSERT INTO books (title, author, year, isbn)
            VALUES (?, ?, ?, ?)
            "#,
        )
        .bind("Book 1")
        .bind("Author A")
        .bind(2020i32)
        .bind("111")
        .execute(&pool)
        .await
        .unwrap();
        
        sqlx::query(
            r#"
            INSERT INTO books (title, author, year, isbn)
            VALUES (?, ?, ?, ?)
            "#,
        )
        .bind("Book 2")
        .bind("Author B")
        .bind(2021i32)
        .bind("222")
        .execute(&pool)
        .await
        .unwrap();
        
        sqlx::query(
            r#"
            INSERT INTO books (title, author, year, isbn)
            VALUES (?, ?, ?, ?)
            "#,
        )
        .bind("Book 3")
        .bind("Author A")
        .bind(2022i32)
        .bind("333")
        .execute(&pool)
        .await
        .unwrap();

        let app = Router::new()
            .route("/books", get(list_books))
            .with_state(pool);

        let server = TestServer::new(app).unwrap();
        
        // Get all books
        let response = server.get("/books").await;
        response.assert_status(StatusCode::OK);
        let body = response.json::<Vec<serde_json::Value>>();
        assert_eq!(body.len(), 3);
        
        // Filter by author
        let response = server.get("/books?author=Author%20A").await;
        response.assert_status(StatusCode::OK);
        let body = response.json::<Vec<serde_json::Value>>();
        assert_eq!(body.len(), 2);
    }

    #[tokio::test]
    async fn test_update_book() {
        let pool = crate::database::init_db(":memory:").await.unwrap();
        let app = Router::new()
            .route("/books", post(create_book_handler))
            .route("/books/{id}", put(update_book_handler))
            .with_state(pool);

        let server = TestServer::new(app).unwrap();
        
        // First create a book
        let create_response = server
            .post("/books")
            .json(&json!({
                "title": "Original Title",
                "author": "Original Author",
                "year": 2020,
                "isbn": "111"
            }))
            .await;
        create_response.assert_status(StatusCode::CREATED);
        let created = create_response.json::<serde_json::Value>();
        let id = created["id"].as_i64().unwrap();
        
        // Update the book
        let response = server
            .put(&format!("/books/{}", id))
            .json(&json!({
                "title": "Updated Title",
                "author": "Updated Author",
                "year": 2021,
                "isbn": "999"
            }))
            .await;
        
        response.assert_status(StatusCode::OK);
        let body = response.json::<serde_json::Value>();
        assert_eq!(body["title"], "Updated Title");
        assert_eq!(body["author"], "Updated Author");
    }

    #[tokio::test]
    async fn test_delete_book() {
        let pool = crate::database::init_db(":memory:").await.unwrap();
        let app = Router::new()
            .route("/books", post(create_book_handler))
            .route("/books/{id}", delete(delete_book_handler))
            .with_state(pool);

        let server = TestServer::new(app).unwrap();
        
        // First create a book
        let create_response = server
            .post("/books")
            .json(&json!({
                "title": "To Delete",
                "author": "Author",
                "year": 2020,
                "isbn": "111"
            }))
            .await;
        create_response.assert_status(StatusCode::CREATED);
        let created = create_response.json::<serde_json::Value>();
        let id = created["id"].as_i64().unwrap();
        
        // Delete the book
        let response = server.delete(&format!("/books/{}", id)).await;
        response.assert_status(StatusCode::NO_CONTENT);
    }

    #[tokio::test]
    async fn test_get_book_by_id_not_found() {
        let pool = crate::database::init_db(":memory:").await.unwrap();
        let app = Router::new()
            .route("/books/{id}", get(get_book))
            .with_state(pool);

        let server = TestServer::new(app).unwrap();
        
        // Try to get a book that doesn't exist
        let response = server.get("/books/999").await;
        response.assert_status(StatusCode::NOT_FOUND);
    }
}
