use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::get,
    Json, Router,
};
use rusqlite::{params, Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::sync::{Arc, Mutex};

pub type Db = Arc<Mutex<Connection>>;

#[derive(Serialize, Debug, Clone)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

#[derive(Deserialize)]
pub struct BookInput {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

#[derive(Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

pub fn open_db(path: &str) -> rusqlite::Result<Db> {
    let conn = Connection::open(path)?;
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT)",
    )?;
    Ok(Arc::new(Mutex::new(conn)))
}

pub fn app(db: Db) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", get(list_books).post(create_book))
        .route("/books/{id}", get(get_book).put(update_book).delete(delete_book))
        .with_state(db)
}

fn err(status: StatusCode, msg: &str) -> Response {
    (status, Json(json!({ "error": msg }))).into_response()
}

fn internal(e: rusqlite::Error) -> Response {
    err(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string())
}

fn validate(input: &BookInput) -> Result<(String, String), Response> {
    let title = input.title.as_deref().map(str::trim).unwrap_or("");
    let author = input.author.as_deref().map(str::trim).unwrap_or("");
    let mut missing = vec![];
    if title.is_empty() { missing.push("title"); }
    if author.is_empty() { missing.push("author"); }
    if !missing.is_empty() {
        return Err(err(StatusCode::BAD_REQUEST, &format!("missing required field(s): {}", missing.join(", "))));
    }
    Ok((title.to_string(), author.to_string()))
}

fn row_to_book(r: &rusqlite::Row) -> rusqlite::Result<Book> {
    Ok(Book { id: r.get(0)?, title: r.get(1)?, author: r.get(2)?, year: r.get(3)?, isbn: r.get(4)? })
}

fn fetch(conn: &Connection, id: i64) -> rusqlite::Result<Option<Book>> {
    conn.query_row("SELECT id,title,author,year,isbn FROM books WHERE id=?1", [id], row_to_book)
        .optional()
}

async fn health() -> Json<serde_json::Value> {
    Json(json!({ "status": "ok" }))
}

async fn create_book(State(db): State<Db>, Json(input): Json<BookInput>) -> Response {
    let (title, author) = match validate(&input) { Ok(v) => v, Err(e) => return e };
    let conn = db.lock().unwrap();
    let res = conn
        .execute("INSERT INTO books (title,author,year,isbn) VALUES (?1,?2,?3,?4)",
            params![title, author, input.year, input.isbn])
        .and_then(|_| fetch(&conn, conn.last_insert_rowid()));
    match res {
        Ok(Some(b)) => (StatusCode::CREATED, Json(b)).into_response(),
        Ok(None) => err(StatusCode::INTERNAL_SERVER_ERROR, "insert failed"),
        Err(e) => internal(e),
    }
}

async fn list_books(State(db): State<Db>, Query(q): Query<ListQuery>) -> Response {
    let conn = db.lock().unwrap();
    let res = (|| {
        let mut stmt = conn.prepare(
            "SELECT id,title,author,year,isbn FROM books WHERE (?1 IS NULL OR author = ?1) ORDER BY id")?;
        let rows = stmt.query_map([q.author], row_to_book)?;
        rows.collect::<rusqlite::Result<Vec<_>>>()
    })();
    match res {
        Ok(books) => Json(books).into_response(),
        Err(e) => internal(e),
    }
}

async fn get_book(State(db): State<Db>, Path(id): Path<i64>) -> Response {
    match fetch(&db.lock().unwrap(), id) {
        Ok(Some(b)) => Json(b).into_response(),
        Ok(None) => err(StatusCode::NOT_FOUND, "book not found"),
        Err(e) => internal(e),
    }
}

async fn update_book(State(db): State<Db>, Path(id): Path<i64>, Json(input): Json<BookInput>) -> Response {
    let (title, author) = match validate(&input) { Ok(v) => v, Err(e) => return e };
    let conn = db.lock().unwrap();
    match conn.execute("UPDATE books SET title=?1,author=?2,year=?3,isbn=?4 WHERE id=?5",
        params![title, author, input.year, input.isbn, id]) {
        Ok(0) => err(StatusCode::NOT_FOUND, "book not found"),
        Ok(_) => match fetch(&conn, id) {
            Ok(Some(b)) => Json(b).into_response(),
            Ok(None) => err(StatusCode::NOT_FOUND, "book not found"),
            Err(e) => internal(e),
        },
        Err(e) => internal(e),
    }
}

async fn delete_book(State(db): State<Db>, Path(id): Path<i64>) -> Response {
    match db.lock().unwrap().execute("DELETE FROM books WHERE id=?1", [id]) {
        Ok(0) => err(StatusCode::NOT_FOUND, "book not found"),
        Ok(_) => StatusCode::NO_CONTENT.into_response(),
        Err(e) => internal(e),
    }
}
