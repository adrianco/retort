use axum::{
    extract::Path,
    http::StatusCode,
    response::IntoResponse,
    routing::{delete, get, post, put},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use sqlx::{SqlitePool, Row};
use std::net::SocketAddr;
use std::{fs};
use uuid::Uuid;

#[derive(Debug, Serialize, Deserialize, Clone, sqlx::FromRow)]
struct Book {
    id: String,
    title: String,
    author: String,
    year: i32,
    isbn: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct BookCreate {
    title: String,
    author: String,
    year: i32,
    isbn: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct BookUpdate {
    title: Option<String>,
    author: Option<String>,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Debug, Clone)]
struct AppState {
    db: SqlitePool,
}

impl AppState {
    async fn init_db() -> Result<SqlitePool, sqlx::Error> {
        // Ensure the directory exists
        fs::create_dir_all("data").unwrap_or_else(|_| ());
        let db = SqlitePool::connect("sqlite:data/books.db").await?;
        sqlx::migrate!().run(&db).await?;
        Ok(db)
    }
}

async fn health_check() -> impl IntoResponse {
    StatusCode::OK
}

async fn create_book(
    app_state: axum::extract::State<AppState>,
    Json(book_data): Json<BookCreate>,
) -> Result<Json<Book>, (StatusCode, String)> {
    if book_data.title.is_empty() {
        return Err((StatusCode::BAD_REQUEST, "Title is required".to_string()));
    }
    if book_data.author.is_empty() {
        return Err((StatusCode::BAD_REQUEST, "Author is required".to_string()));
    }

    let id = Uuid::new_v4().to_string();
    let book = Book {
        id: id.clone(),
        title: book_data.title,
        author: book_data.author,
        year: book_data.year,
        isbn: book_data.isbn,
    };

    let result = sqlx::query(
        r#"
        INSERT INTO books (id, title, author, year, isbn)
        VALUES (?, ?, ?, ?, ?)
        "#,
    )
    .bind(&id)
    .bind(&book.title)
    .bind(&book.author)
    .bind(book.year)
    .bind(&book.isbn)
    .execute(&app_state.db)
    .await;

    match result {
        Ok(_) => Ok(Json(book)),
        Err(e) => Err((StatusCode::INTERNAL_SERVER_ERROR, format!("Database error: {}", e))),
    }
}

async fn get_books(
    app_state: axum::extract::State<AppState>,
    author: Option<String>,
) -> Result<Json<Vec<Book>>, (StatusCode, String)> {
    let query = if let Some(author_filter) = author {
        sqlx::query_as::<_, Book>(
            r#"
            SELECT id, title, author, year, isbn
            FROM books
            WHERE author LIKE ?
            "#,
        )
        .bind(format!("%{}%", author_filter))
    } else {
        sqlx::query_as::<_, Book>(
            r#"
            SELECT id, title, author, year, isbn
            FROM books
            "#,
        )
    };

    let books = query.fetch_all(&app_state.db).await;

    match books {
        Ok(rows) => Ok(Json(rows)),
        Err(e) => Err((StatusCode::INTERNAL_SERVER_ERROR, format!("Database error: {}", e))),
    }
}

async fn get_book(
    app_state: axum::extract::State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<Book>, (StatusCode, String)> {
    let book = sqlx::query_as::<_, Book>(
        r#"
        SELECT id, title, author, year, isbn
        FROM books
        WHERE id = ?
        "#,
    )
    .bind(id)
    .fetch_one(&app_state.db)
    .await;

    match book {
        Ok(row) => Ok(Json(row)),
        Err(sqlx::Error::RowNotFound) => {
            Err((StatusCode::NOT_FOUND, "Book not found".to_string()))
        }
        Err(e) => Err((StatusCode::INTERNAL_SERVER_ERROR, format!("Database error: {}", e))),
    }
}

async fn update_book(
    app_state: axum::extract::State<AppState>,
    Path(id): Path<String>,
    Json(update_data): Json<BookUpdate>,
) -> Result<Json<Book>, (StatusCode, String)> {
    // Check if book exists
    let existing_book = sqlx::query_as::<_, Book>(
        r#"
        SELECT id, title, author, year, isbn
        FROM books
        WHERE id = ?
        "#,
    )
    .bind(&id)
    .fetch_one(&app_state.db)
    .await;

    if let Err(sqlx::Error::RowNotFound) = existing_book {
        return Err((StatusCode::NOT_FOUND, "Book not found".to_string()));
    }

    // Simple approach - if any fields are provided, update them all
    let title = update_data.title.unwrap_or_else(|| existing_book.as_ref().unwrap().title.clone());
    let author = update_data.author.unwrap_or_else(|| existing_book.as_ref().unwrap().author.clone());
    let year = update_data.year.unwrap_or(existing_book.as_ref().unwrap().year);
    let isbn = update_data.isbn.unwrap_or_else(|| existing_book.as_ref().unwrap().isbn.clone());

    let result = sqlx::query(
        r#"
        UPDATE books
        SET title = ?, author = ?, year = ?, isbn = ?
        WHERE id = ?
        "#,
    )
    .bind(&title)
    .bind(&author)
    .bind(year)
    .bind(&isbn)
    .bind(&id)
    .execute(&app_state.db)
    .await;

    match result {
        Ok(_) => {
            // Fetch the updated book
            let updated_book = sqlx::query_as::<_, Book>(
                r#"
                SELECT id, title, author, year, isbn
                FROM books
                WHERE id = ?
                "#,
            )
            .bind(id)
            .fetch_one(&app_state.db)
            .await;

            match updated_book {
                Ok(book) => Ok(Json(book)),
                Err(e) => Err((StatusCode::INTERNAL_SERVER_ERROR, format!("Database error: {}", e))),
            }
        }
        Err(e) => Err((StatusCode::INTERNAL_SERVER_ERROR, format!("Database error: {}", e))),
    }
}

async fn delete_book(
    app_state: axum::extract::State<AppState>,
    Path(id): Path<String>,
) -> Result<StatusCode, (StatusCode, String)> {
    let result = sqlx::query(
        r#"
        DELETE FROM books
        WHERE id = ?
        "#,
    )
    .bind(id)
    .execute(&app_state.db)
    .await;

    match result {
        Ok(row) => {
            if row.rows_affected() > 0 {
                Ok(StatusCode::NO_CONTENT)
            } else {
                Err((StatusCode::NOT_FOUND, "Book not found".to_string()))
            }
        }
        Err(e) => Err((StatusCode::INTERNAL_SERVER_ERROR, format!("Database error: {}", e))),
    }
}

#[tokio::main]
async fn main() {
    // Initialize the database
    let db = AppState::init_db().await.expect("Failed to initialize database");
    let app_state = AppState { db };

    let app = Router::new()
        .route("/health", get(health_check))
        .route("/books", post(create_book))
        .route("/books", get(get_books))
        .route("/books/:id", get(get_book))
        .route("/books/:id", put(update_book))
        .route("/books/:id", delete(delete_book))
        .with_state(app_state);

    let addr = SocketAddr::from(([127, 0, 0, 1], 3000));
    println!("Server running on http://{}", addr);

    // Use the correct server import
    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}