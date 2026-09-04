use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::Response,
    routing::{delete, get, post, put},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use sqlx::{Sqlite, SqlitePool};
use std::net::SocketAddr;
use std::sync::Arc;

#[derive(Serialize, Deserialize, Debug, Clone)]
struct Book {
    id: Option<i32>,
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Serialize, Deserialize)]
struct NewBook {
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Serialize, Deserialize)]
struct UpdateBook {
    title: Option<String>,
    author: Option<String>,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Serialize, Deserialize)]
struct HealthResponse {
    status: String,
}

#[derive(Serialize, Deserialize)]
struct Error {
    message: String,
}

// State to hold the database connection pool
struct AppState {
    db: SqlitePool,
}

// Initialize the database and create the books table if it doesn't exist
async fn init_db() -> SqlitePool {
    let db_url = "sqlite:books.db";
    let pool = SqlitePool::connect(db_url).await.unwrap();
    
    // Create the books table
    sqlx::execute(
        r#"
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )
        "#,
    )
    .execute(&pool)
    .await
    .unwrap();
    
    pool
}

// Health check endpoint
async fn health() -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "OK".to_string(),
    })
}

// Create a new book
async fn create_book(
    State(state): State<Arc<AppState>>,
    Json(input): Json<NewBook>,
) -> Result<Json<Book>, (StatusCode, Json<Error>)> {
    // Validate input - title and author are required
    if input.title.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(Error {
                message: "Title is required".to_string(),
            }),
        ));
    }
    
    if input.author.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(Error {
                message: "Author is required".to_string(),
            }),
        ));
    }

    let new_book = Book {
        id: None,
        title: input.title,
        author: input.author,
        year: input.year,
        isbn: input.isbn,
    };

    let inserted_book = sqlx::query_as::<_, Book>(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING id, title, author, year, isbn",
    )
    .bind(&new_book.title)
    .bind(&new_book.author)
    .bind(new_book.year)
    .bind(new_book.isbn.as_deref())
    .fetch_one(&state.db)
    .await
    .map_err(|e| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(Error {
                message: format!("Database error: {}", e),
            }),
        )
    })?;

    Ok(Json(inserted_book))
}

// Get all books with optional author filter
async fn get_books(
    State(state): State<Arc<AppState>>,
    author: Option<String>,
) -> Result<Json<Vec<Book>>, (StatusCode, Json<Error>)> {
    let books = if let Some(author_filter) = author {
        sqlx::query_as::<_, Book>(
            "SELECT id, title, author, year, isbn FROM books WHERE author = ?",
        )
        .bind(author_filter)
        .fetch_all(&state.db)
        .await
        .map_err(|e| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(Error {
                    message: format!("Database error: {}", e),
                }),
            )
        })?
    } else {
        sqlx::query_as::<_, Book>("SELECT id, title, author, year, isbn FROM books")
            .fetch_all(&state.db)
            .await
            .map_err(|e| {
                (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    Json(Error {
                        message: format!("Database error: {}", e),
                    }),
                )
            })?
    };

    Ok(Json(books))
}

// Get a single book by ID
async fn get_book_by_id(
    State(state): State<Arc<AppState>>,
    Path(id): Path<i32>,
) -> Result<Json<Book>, (StatusCode, Json<Error>)> {
    let book = sqlx::query_as::<_, Book>("SELECT id, title, author, year, isbn FROM books WHERE id = ?")
        .bind(id)
        .fetch_one(&state.db)
        .await;

    match book {
        Ok(book) => Ok(Json(book)),
        Err(_) => Err((
            StatusCode::NOT_FOUND,
            Json(Error {
                message: "Book not found".to_string(),
            }),
        )),
    }
}

// Update a book
async fn update_book(
    State(state): State<Arc<AppState>>,
    Path(id): Path<i32>,
    Json(input): Json<UpdateBook>,
) -> Result<Json<Book>, (StatusCode, Json<Error>)> {
    // Check if the book exists
    let existing_book = sqlx::query_as::<_, Book>("SELECT * FROM books WHERE id = ?")
        .bind(id)
        .fetch_one(&state.db)
        .await
        .map_err(|e| {
            (
                StatusCode::NOT_FOUND,
                Json(Error {
                    message: "Book not found".to_string(),
                }),
            )
        })?;

    // Prepare the update query
    let title = input.title.clone().unwrap_or(existing_book.title);
    let author = input.author.clone().unwrap_or(existing_book.author);
    let year = input.year.or(existing_book.year);
    let isbn = input.isbn.clone().or(existing_book.isbn);

    // Validate that author and title are not empty
    if title.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(Error {
                message: "Title cannot be empty".to_string(),
            }),
        ));
    }
    
    if author.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(Error {
                message: "Author cannot be empty".to_string(),
            }),
        ));
    }

    let updated_book = sqlx::query_as::<_, Book>(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ? RETURNING id, title, author, year, isbn",
    )
    .bind(&title)
    .bind(&author)
    .bind(year)
    .bind(isbn.as_deref())
    .bind(id)
    .fetch_one(&state.db)
    .await
    .map_err(|e| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(Error {
                message: format!("Database error: {}", e),
            }),
        )
    })?;

    Ok(Json(updated_book))
}

// Delete a book
async fn delete_book(
    State(state): State<Arc<AppState>>,
    Path(id): Path<i32>,
) -> Result<StatusCode, (StatusCode, Json<Error>)> {
    let result = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(id)
        .execute(&state.db)
        .await
        .map_err(|e| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(Error {
                    message: format!("Database error: {}", e),
                }),
            )
        })?;

    if result.rows_affected() == 0 {
        return Err((
            StatusCode::NOT_FOUND,
            Json(Error {
                message: "Book not found".to_string(),
            }),
        ));
    }

    Ok(StatusCode::NO_CONTENT)
}

// Main function to start the server
#[tokio::main]
async fn main() {
    // Initialize database
    let db = init_db().await;
    let app_state = Arc::new(AppState { db });

    // Build the router
    let app = Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book).get(get_books))
        .route("/books/:id", get(get_book_by_id).put(update_book).delete(delete_book));

    // Bind to address
    let addr = SocketAddr::from(([127, 0, 0, 1], 8080));
    println!("Server running on http://{}", addr);

    // Start the server
    axum::Server::bind(&addr)
        .serve(app.with_state(app_state).into_make_service())
        .await
        .unwrap();
}
