use std::sync::{Arc, Mutex};

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::Json,
    routing::get,
    Router,
};
use rusqlite::{params, Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};

pub type Db = Arc<Mutex<Connection>>;

#[derive(Debug, Clone, Serialize)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct BookInput {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct ListParams {
    pub author: Option<String>,
}

type ApiError = (StatusCode, Json<Value>);

fn error(status: StatusCode, message: &str) -> ApiError {
    (status, Json(json!({ "error": message })))
}

fn db_error(err: rusqlite::Error) -> ApiError {
    error(
        StatusCode::INTERNAL_SERVER_ERROR,
        &format!("database error: {err}"),
    )
}

fn validate(input: &BookInput) -> Result<(String, String), ApiError> {
    let title = input.title.as_deref().unwrap_or("").trim().to_string();
    let author = input.author.as_deref().unwrap_or("").trim().to_string();
    if title.is_empty() {
        return Err(error(StatusCode::BAD_REQUEST, "title is required"));
    }
    if author.is_empty() {
        return Err(error(StatusCode::BAD_REQUEST, "author is required"));
    }
    Ok((title, author))
}

pub fn init_db(conn: &Connection) -> rusqlite::Result<()> {
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            title  TEXT NOT NULL,
            author TEXT NOT NULL,
            year   INTEGER,
            isbn   TEXT
        )",
    )
}

pub fn new_db(path: Option<&str>) -> rusqlite::Result<Db> {
    let conn = match path {
        Some(p) => Connection::open(p)?,
        None => Connection::open_in_memory()?,
    };
    init_db(&conn)?;
    Ok(Arc::new(Mutex::new(conn)))
}

pub fn app(db: Db) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", get(list_books).post(create_book))
        .route(
            "/books/{id}",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(db)
}

async fn health() -> Json<Value> {
    Json(json!({ "status": "ok" }))
}

async fn create_book(
    State(db): State<Db>,
    Json(input): Json<BookInput>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    let (title, author) = validate(&input)?;
    let conn = db.lock().unwrap();
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![title, author, input.year, input.isbn],
    )
    .map_err(db_error)?;
    let book = Book {
        id: conn.last_insert_rowid(),
        title,
        author,
        year: input.year,
        isbn: input.isbn,
    };
    Ok((StatusCode::CREATED, Json(book)))
}

async fn list_books(
    State(db): State<Db>,
    Query(params): Query<ListParams>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let conn = db.lock().unwrap();
    let row_to_book = |row: &rusqlite::Row| -> rusqlite::Result<Book> {
        Ok(Book {
            id: row.get(0)?,
            title: row.get(1)?,
            author: row.get(2)?,
            year: row.get(3)?,
            isbn: row.get(4)?,
        })
    };
    let books = match &params.author {
        Some(author) => {
            let mut stmt = conn
                .prepare(
                    "SELECT id, title, author, year, isbn FROM books
                     WHERE author = ?1 ORDER BY id",
                )
                .map_err(db_error)?;
            let rows = stmt
                .query_map([author], row_to_book)
                .map_err(db_error)?
                .collect::<rusqlite::Result<Vec<_>>>()
                .map_err(db_error)?;
            rows
        }
        None => {
            let mut stmt = conn
                .prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")
                .map_err(db_error)?;
            let rows = stmt
                .query_map([], row_to_book)
                .map_err(db_error)?
                .collect::<rusqlite::Result<Vec<_>>>()
                .map_err(db_error)?;
            rows
        }
    };
    Ok(Json(books))
}

fn find_book(conn: &Connection, id: i64) -> Result<Option<Book>, ApiError> {
    conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        [id],
        |row| {
            Ok(Book {
                id: row.get(0)?,
                title: row.get(1)?,
                author: row.get(2)?,
                year: row.get(3)?,
                isbn: row.get(4)?,
            })
        },
    )
    .optional()
    .map_err(db_error)
}

async fn get_book(State(db): State<Db>, Path(id): Path<i64>) -> Result<Json<Book>, ApiError> {
    let conn = db.lock().unwrap();
    match find_book(&conn, id)? {
        Some(book) => Ok(Json(book)),
        None => Err(error(StatusCode::NOT_FOUND, "book not found")),
    }
}

async fn update_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
    Json(input): Json<BookInput>,
) -> Result<Json<Book>, ApiError> {
    let (title, author) = validate(&input)?;
    let conn = db.lock().unwrap();
    let updated = conn
        .execute(
            "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
            params![title, author, input.year, input.isbn, id],
        )
        .map_err(db_error)?;
    if updated == 0 {
        return Err(error(StatusCode::NOT_FOUND, "book not found"));
    }
    Ok(Json(Book {
        id,
        title,
        author,
        year: input.year,
        isbn: input.isbn,
    }))
}

async fn delete_book(State(db): State<Db>, Path(id): Path<i64>) -> Result<StatusCode, ApiError> {
    let conn = db.lock().unwrap();
    let deleted = conn
        .execute("DELETE FROM books WHERE id = ?1", [id])
        .map_err(db_error)?;
    if deleted == 0 {
        return Err(error(StatusCode::NOT_FOUND, "book not found"));
    }
    Ok(StatusCode::NO_CONTENT)
}
