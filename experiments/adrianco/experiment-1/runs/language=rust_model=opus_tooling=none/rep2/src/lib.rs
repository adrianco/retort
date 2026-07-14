use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

pub type Db = Arc<Mutex<Connection>>;

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
pub struct Book {
    pub id: String,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct BookInput {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Serialize)]
struct ErrorBody {
    error: String,
}

pub struct ApiError(StatusCode, String);

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        (self.0, Json(ErrorBody { error: self.1 })).into_response()
    }
}

pub fn init_db(path: &str) -> rusqlite::Result<Connection> {
    let conn = Connection::open(path)?;
    conn.execute(
        "CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )",
        [],
    )?;
    Ok(conn)
}

pub fn build_app(db: Db) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book).get(list_books))
        .route("/books/:id", get(get_book).put(update_book).delete(delete_book))
        .with_state(db)
}

async fn health() -> impl IntoResponse {
    (StatusCode::OK, Json(serde_json::json!({"status": "ok"})))
}

fn validate(input: &BookInput) -> Result<(String, String), ApiError> {
    let title = input.title.as_deref().unwrap_or("").trim().to_string();
    let author = input.author.as_deref().unwrap_or("").trim().to_string();
    if title.is_empty() {
        return Err(ApiError(StatusCode::BAD_REQUEST, "title is required".into()));
    }
    if author.is_empty() {
        return Err(ApiError(StatusCode::BAD_REQUEST, "author is required".into()));
    }
    Ok((title, author))
}

async fn create_book(
    State(db): State<Db>,
    Json(input): Json<BookInput>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    let (title, author) = validate(&input)?;
    let id = uuid::Uuid::new_v4().to_string();
    let book = Book {
        id: id.clone(),
        title,
        author,
        year: input.year,
        isbn: input.isbn,
    };
    let conn = db.lock().unwrap();
    conn.execute(
        "INSERT INTO books (id, title, author, year, isbn) VALUES (?1, ?2, ?3, ?4, ?5)",
        params![book.id, book.title, book.author, book.year, book.isbn],
    )
    .map_err(|e| ApiError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    Ok((StatusCode::CREATED, Json(book)))
}

async fn list_books(
    State(db): State<Db>,
    Query(params): Query<HashMap<String, String>>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let conn = db.lock().unwrap();
    let (sql, args): (&str, Vec<String>) = match params.get("author") {
        Some(a) => (
            "SELECT id, title, author, year, isbn FROM books WHERE author = ?1",
            vec![a.clone()],
        ),
        None => ("SELECT id, title, author, year, isbn FROM books", vec![]),
    };
    let mut stmt = conn
        .prepare(sql)
        .map_err(|e| ApiError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    let rows = stmt
        .query_map(rusqlite::params_from_iter(args.iter()), row_to_book)
        .map_err(|e| ApiError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    let mut books = Vec::new();
    for r in rows {
        books.push(r.map_err(|e| ApiError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?);
    }
    Ok(Json(books))
}

fn row_to_book(row: &rusqlite::Row) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

async fn get_book(State(db): State<Db>, Path(id): Path<String>) -> Result<Json<Book>, ApiError> {
    let conn = db.lock().unwrap();
    let book = conn
        .query_row(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
            params![id],
            row_to_book,
        )
        .map_err(|e| match e {
            rusqlite::Error::QueryReturnedNoRows => {
                ApiError(StatusCode::NOT_FOUND, "book not found".into())
            }
            _ => ApiError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()),
        })?;
    Ok(Json(book))
}

async fn update_book(
    State(db): State<Db>,
    Path(id): Path<String>,
    Json(input): Json<BookInput>,
) -> Result<Json<Book>, ApiError> {
    let (title, author) = validate(&input)?;
    let conn = db.lock().unwrap();
    let affected = conn
        .execute(
            "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
            params![title, author, input.year, input.isbn, id],
        )
        .map_err(|e| ApiError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    if affected == 0 {
        return Err(ApiError(StatusCode::NOT_FOUND, "book not found".into()));
    }
    Ok(Json(Book {
        id,
        title,
        author,
        year: input.year,
        isbn: input.isbn,
    }))
}

async fn delete_book(State(db): State<Db>, Path(id): Path<String>) -> Result<StatusCode, ApiError> {
    let conn = db.lock().unwrap();
    let affected = conn
        .execute("DELETE FROM books WHERE id = ?1", params![id])
        .map_err(|e| ApiError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    if affected == 0 {
        return Err(ApiError(StatusCode::NOT_FOUND, "book not found".into()));
    }
    Ok(StatusCode::NO_CONTENT)
}
