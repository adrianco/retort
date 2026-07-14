use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::IntoResponse,
    routing::{delete, get, post, put},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use sqlx::{SqlitePool, Row};
use std::sync::Arc;
use uuid::Uuid;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Book {
    pub id: Option<Uuid>,
    pub title: String,
    pub author: String,
    pub year: i32,
    pub isbn: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct BookResponse {
    pub id: Uuid,
    pub title: String,
    pub author: String,
    pub year: i32,
    pub isbn: String,
}

impl From<Book> for BookResponse {
    fn from(book: Book) -> Self {
        BookResponse {
            id: book.id.unwrap(),
            title: book.title,
            author: book.author,
            year: book.year,
            isbn: book.isbn,
        }
    }
}

#[derive(Debug, Serialize, Deserialize)]
pub struct CreateBookRequest {
    pub title: String,
    pub author: String,
    pub year: i32,
    pub isbn: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct UpdateBookRequest {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Clone)]
pub struct AppState {
    pub db: SqlitePool,
}

impl AppState {
    pub async fn new() -> Result<Self, sqlx::Error> {
        let db = SqlitePool::connect("sqlite::memory:").await?;
        
        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS books (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER NOT NULL,
                isbn TEXT NOT NULL
            )
            "#,
        )
        .execute(&db)
        .await?;

        Ok(AppState { db })
    }
}

pub async fn create_book(
    State(state): State<Arc<AppState>>,
    Json(payload): Json<CreateBookRequest>,
) -> Result<impl IntoResponse, StatusCode> {
    // Validate required fields
    if payload.title.is_empty() {
        return Err(StatusCode::BAD_REQUEST);
    }
    if payload.author.is_empty() {
        return Err(StatusCode::BAD_REQUEST);
    }

    let id = Uuid::new_v4();
    
    let book = Book {
        id: Some(id),
        title: payload.title,
        author: payload.author,
        year: payload.year,
        isbn: payload.isbn,
    };

    let result = sqlx::query(
        r#"
        INSERT INTO books (id, title, author, year, isbn)
        VALUES ($1, $2, $3, $4, $5)
        "#,
    )
    .bind(book.id.unwrap().to_string())
    .bind(&book.title)
    .bind(&book.author)
    .bind(book.year)
    .bind(&book.isbn)
    .execute(&state.db)
    .await;

    match result {
        Ok(_) => {
            let response = BookResponse::from(book);
            Ok((StatusCode::CREATED, Json(response)))
        }
        Err(_) => Err(StatusCode::INTERNAL_SERVER_ERROR),
    }
}

pub async fn get_books(
    State(state): State<Arc<AppState>>,
    author: Option<String>,
) -> Result<impl IntoResponse, StatusCode> {
    let query = if let Some(author_filter) = author {
        sqlx::query(
            r#"
            SELECT id, title, author, year, isbn
            FROM books
            WHERE author = $1
            "#,
        )
        .bind(author_filter)
    } else {
        sqlx::query(
            r#"
            SELECT id, title, author, year, isbn
            FROM books
            "#,
        )
    };

    let rows = query
        .fetch_all(&state.db)
        .await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let mut books: Vec<BookResponse> = Vec::new();
    
    for row in rows {
        let book = Book {
            id: Some(Uuid::parse_str(row.get(0)).map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?),
            title: row.get(1),
            author: row.get(2),
            year: row.get(3),
            isbn: row.get(4),
        };
        books.push(BookResponse::from(book));
    }

    Ok(Json(books))
}

pub async fn get_book(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
) -> Result<impl IntoResponse, StatusCode> {
    let book_id = Uuid::parse_str(&id).map_err(|_| StatusCode::BAD_REQUEST)?;

    let row = sqlx::query(
        r#"
        SELECT id, title, author, year, isbn
        FROM books
        WHERE id = $1
        "#,
    )
    .bind(book_id.to_string())
    .fetch_one(&state.db)
    .await;

    match row {
        Ok(row) => {
            let book = Book {
                id: Some(book_id),
                title: row.get(1),
                author: row.get(2),
                year: row.get(3),
                isbn: row.get(4),
            };
            let response = BookResponse::from(book);
            Ok(Json(response))
        }
        Err(sqlx::Error::RowNotFound) => Err(StatusCode::NOT_FOUND),
        Err(_) => Err(StatusCode::INTERNAL_SERVER_ERROR),
    }
}

pub async fn update_book(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
    Json(payload): Json<UpdateBookRequest>,
) -> Result<impl IntoResponse, StatusCode> {
    let book_id = Uuid::parse_str(&id).map_err(|_| StatusCode::BAD_REQUEST)?;

    // First check if the book exists
    let existing_book = sqlx::query(
        r#"
        SELECT id, title, author, year, isbn
        FROM books
        WHERE id = $1
        "#,
    )
    .bind(book_id.to_string())
    .fetch_one(&state.db)
    .await;

    if let Err(sqlx::Error::RowNotFound) = existing_book {
        return Err(StatusCode::NOT_FOUND);
    }

    // Simple update implementation - update all fields if provided
    let title = payload.title.unwrap_or_default();
    let author = payload.author.unwrap_or_default();
    let year = payload.year.unwrap_or(0);
    let isbn = payload.isbn.unwrap_or_default();

    let result = sqlx::query(
        r#"
        UPDATE books 
        SET title = $1, author = $2, year = $3, isbn = $4
        WHERE id = $5
        "#,
    )
    .bind(&title)
    .bind(&author)
    .bind(year)
    .bind(&isbn)
    .bind(book_id.to_string())
    .execute(&state.db)
    .await;

    match result {
        Ok(_) => {
            // Fetch and return the updated book
            let row = sqlx::query(
                r#"
                SELECT id, title, author, year, isbn
                FROM books
                WHERE id = $1
                "#,
            )
            .bind(book_id.to_string())
            .fetch_one(&state.db)
            .await
            .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

            let book = Book {
                id: Some(book_id),
                title: row.get(1),
                author: row.get(2),
                year: row.get(3),
                isbn: row.get(4),
            };
            let response = BookResponse::from(book);
            Ok(Json(response))
        }
        Err(_) => Err(StatusCode::INTERNAL_SERVER_ERROR),
    }
}

pub async fn delete_book(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
) -> Result<impl IntoResponse, StatusCode> {
    let book_id = Uuid::parse_str(&id).map_err(|_| StatusCode::BAD_REQUEST)?;

    let result = sqlx::query(
        r#"
        DELETE FROM books
        WHERE id = $1
        "#,
    )
    .bind(book_id.to_string())
    .execute(&state.db)
    .await;

    match result {
        Ok(result) => {
            if result.rows_affected() == 0 {
                Err(StatusCode::NOT_FOUND)
            } else {
                Ok(StatusCode::NO_CONTENT)
            }
        }
        Err(_) => Err(StatusCode::INTERNAL_SERVER_ERROR),
    }
}

pub async fn health_check() -> impl IntoResponse {
    Json(serde_json::json!({ "status": "healthy" }))
}

pub fn create_app(state: Arc<AppState>) -> Router {
    Router::new()
        .route("/books", post(create_book))
        .route("/books", get(get_books))
        .route("/books/:id", get(get_book))
        .route("/books/:id", put(update_book))
        .route("/books/:id", delete(delete_book))
        .route("/health", get(health_check))
        .with_state(state)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_book_struct() {
        let book = Book {
            id: Some(Uuid::new_v4()),
            title: "Test Title".to_string(),
            author: "Test Author".to_string(),
            year: 2023,
            isbn: "1234567890".to_string(),
        };

        assert_eq!(book.title, "Test Title");
        assert_eq!(book.author, "Test Author");
        assert_eq!(book.year, 2023);
        assert_eq!(book.isbn, "1234567890");
    }
}