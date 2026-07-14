//! A small REST API for managing a book collection, backed by SQLite.

use std::sync::{Arc, Mutex};

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use rusqlite::Connection;
use serde::{Deserialize, Serialize};
use serde_json::json;

/// Shared application state: a single SQLite connection behind a mutex.
///
/// rusqlite is synchronous, so a mutex keeps access serialized. This is plenty
/// for a small service and keeps the code simple.
pub type Db = Arc<Mutex<Connection>>;

/// A book as stored and returned by the API.
#[derive(Debug, Serialize, PartialEq)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

/// The payload accepted when creating or updating a book.
#[derive(Debug, Deserialize)]
pub struct BookInput {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

/// Query parameters for listing books.
#[derive(Debug, Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

/// Create the table if it does not already exist.
pub fn init_db(conn: &Connection) -> rusqlite::Result<()> {
    conn.execute(
        "CREATE TABLE IF NOT EXISTS books (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            title  TEXT NOT NULL,
            author TEXT NOT NULL,
            year   INTEGER,
            isbn   TEXT
        )",
        [],
    )?;
    Ok(())
}

/// Open an in-memory database, useful for tests.
pub fn in_memory_db() -> Db {
    let conn = Connection::open_in_memory().expect("open in-memory db");
    init_db(&conn).expect("init db");
    Arc::new(Mutex::new(conn))
}

/// Open (or create) a file-backed database.
pub fn file_db(path: &str) -> Db {
    let conn = Connection::open(path).expect("open db file");
    init_db(&conn).expect("init db");
    Arc::new(Mutex::new(conn))
}

/// Build the application router with all routes wired up.
pub fn app(db: Db) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book).get(list_books))
        .route(
            "/books/:id",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(db)
}

/// Helper to build a JSON error response with a status code.
fn error(status: StatusCode, message: &str) -> Response {
    (status, Json(json!({ "error": message }))).into_response()
}

/// Validate required fields, returning cleaned (trimmed) title and author.
fn validate(input: &BookInput) -> Result<(String, String), Response> {
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

/// Map a SQLite row to a `Book`.
fn row_to_book(row: &rusqlite::Row) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get("id")?,
        title: row.get("title")?,
        author: row.get("author")?,
        year: row.get("year")?,
        isbn: row.get("isbn")?,
    })
}

/// GET /health
async fn health() -> Response {
    (StatusCode::OK, Json(json!({ "status": "ok" }))).into_response()
}

/// POST /books
async fn create_book(State(db): State<Db>, Json(input): Json<BookInput>) -> Response {
    let (title, author) = match validate(&input) {
        Ok(v) => v,
        Err(resp) => return resp,
    };

    let conn = db.lock().unwrap();
    let result = conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        rusqlite::params![title, author, input.year, input.isbn],
    );

    if let Err(e) = result {
        return error(
            StatusCode::INTERNAL_SERVER_ERROR,
            &format!("database error: {e}"),
        );
    }

    let id = conn.last_insert_rowid();
    let book = Book {
        id,
        title,
        author,
        year: input.year,
        isbn: input.isbn,
    };
    (StatusCode::CREATED, Json(book)).into_response()
}

/// GET /books  (optional ?author= filter)
async fn list_books(State(db): State<Db>, Query(q): Query<ListQuery>) -> Response {
    let conn = db.lock().unwrap();

    let books: rusqlite::Result<Vec<Book>> = match q.author {
        Some(author) => {
            let mut stmt = conn
                .prepare("SELECT id, title, author, year, isbn FROM books WHERE author = ?1 ORDER BY id")
                .unwrap();
            let rows = stmt
                .query_map([author], row_to_book)
                .unwrap()
                .collect();
            rows
        }
        None => {
            let mut stmt = conn
                .prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")
                .unwrap();
            let rows = stmt.query_map([], row_to_book).unwrap().collect();
            rows
        }
    };

    match books {
        Ok(books) => (StatusCode::OK, Json(books)).into_response(),
        Err(e) => error(
            StatusCode::INTERNAL_SERVER_ERROR,
            &format!("database error: {e}"),
        ),
    }
}

/// GET /books/{id}
async fn get_book(State(db): State<Db>, Path(id): Path<i64>) -> Response {
    let conn = db.lock().unwrap();
    let mut stmt = conn
        .prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?1")
        .unwrap();
    let book = stmt.query_row([id], row_to_book);

    match book {
        Ok(book) => (StatusCode::OK, Json(book)).into_response(),
        Err(rusqlite::Error::QueryReturnedNoRows) => {
            error(StatusCode::NOT_FOUND, "book not found")
        }
        Err(e) => error(
            StatusCode::INTERNAL_SERVER_ERROR,
            &format!("database error: {e}"),
        ),
    }
}

/// PUT /books/{id}
async fn update_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
    Json(input): Json<BookInput>,
) -> Response {
    let (title, author) = match validate(&input) {
        Ok(v) => v,
        Err(resp) => return resp,
    };

    let conn = db.lock().unwrap();
    let changed = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        rusqlite::params![title, author, input.year, input.isbn, id],
    );

    match changed {
        Ok(0) => error(StatusCode::NOT_FOUND, "book not found"),
        Ok(_) => {
            let book = Book {
                id,
                title,
                author,
                year: input.year,
                isbn: input.isbn,
            };
            (StatusCode::OK, Json(book)).into_response()
        }
        Err(e) => error(
            StatusCode::INTERNAL_SERVER_ERROR,
            &format!("database error: {e}"),
        ),
    }
}

/// DELETE /books/{id}
async fn delete_book(State(db): State<Db>, Path(id): Path<i64>) -> Response {
    let conn = db.lock().unwrap();
    let changed = conn.execute("DELETE FROM books WHERE id = ?1", [id]);

    match changed {
        Ok(0) => error(StatusCode::NOT_FOUND, "book not found"),
        Ok(_) => StatusCode::NO_CONTENT.into_response(),
        Err(e) => error(
            StatusCode::INTERNAL_SERVER_ERROR,
            &format!("database error: {e}"),
        ),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::http::{Request, StatusCode};
    use http_body_util::BodyExt;
    use serde_json::Value;
    use tower::ServiceExt; // for `oneshot`

    async fn send(db: Db, method: &str, uri: &str, body: Option<Value>) -> (StatusCode, Value) {
        let req = Request::builder().method(method).uri(uri);
        let req = match body {
            Some(b) => req
                .header("content-type", "application/json")
                .body(Body::from(b.to_string()))
                .unwrap(),
            None => req.body(Body::empty()).unwrap(),
        };
        let resp = app(db).oneshot(req).await.unwrap();
        let status = resp.status();
        let bytes = resp.into_body().collect().await.unwrap().to_bytes();
        let value = if bytes.is_empty() {
            Value::Null
        } else {
            serde_json::from_slice(&bytes).unwrap()
        };
        (status, value)
    }

    #[tokio::test]
    async fn health_check_works() {
        let db = in_memory_db();
        let (status, body) = send(db, "GET", "/health", None).await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(body["status"], "ok");
    }

    #[tokio::test]
    async fn create_and_get_book() {
        let db = in_memory_db();
        let payload = json!({
            "title": "The Rust Programming Language",
            "author": "Steve Klabnik",
            "year": 2019,
            "isbn": "978-1718500440"
        });
        let (status, body) = send(db.clone(), "POST", "/books", Some(payload)).await;
        assert_eq!(status, StatusCode::CREATED);
        assert_eq!(body["title"], "The Rust Programming Language");
        assert_eq!(body["year"], 2019);
        let id = body["id"].as_i64().unwrap();

        let (status, body) = send(db, "GET", &format!("/books/{id}"), None).await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(body["author"], "Steve Klabnik");
    }

    #[tokio::test]
    async fn create_requires_title_and_author() {
        let db = in_memory_db();

        let (status, body) =
            send(db.clone(), "POST", "/books", Some(json!({ "author": "Nobody" }))).await;
        assert_eq!(status, StatusCode::BAD_REQUEST);
        assert_eq!(body["error"], "title is required");

        let (status, body) = send(
            db.clone(),
            "POST",
            "/books",
            Some(json!({ "title": "   ", "author": "Nobody" })),
        )
        .await;
        assert_eq!(status, StatusCode::BAD_REQUEST);
        assert_eq!(body["error"], "title is required");

        let (status, body) =
            send(db, "POST", "/books", Some(json!({ "title": "A Title" }))).await;
        assert_eq!(status, StatusCode::BAD_REQUEST);
        assert_eq!(body["error"], "author is required");
    }

    #[tokio::test]
    async fn list_with_author_filter() {
        let db = in_memory_db();
        for (title, author) in [
            ("Book A", "Alice"),
            ("Book B", "Bob"),
            ("Book C", "Alice"),
        ] {
            send(
                db.clone(),
                "POST",
                "/books",
                Some(json!({ "title": title, "author": author })),
            )
            .await;
        }

        let (status, body) = send(db.clone(), "GET", "/books", None).await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(body.as_array().unwrap().len(), 3);

        let (status, body) = send(db, "GET", "/books?author=Alice", None).await;
        assert_eq!(status, StatusCode::OK);
        let arr = body.as_array().unwrap();
        assert_eq!(arr.len(), 2);
        assert!(arr.iter().all(|b| b["author"] == "Alice"));
    }

    #[tokio::test]
    async fn update_book_changes_fields() {
        let db = in_memory_db();
        let (_, body) = send(
            db.clone(),
            "POST",
            "/books",
            Some(json!({ "title": "Old", "author": "Author" })),
        )
        .await;
        let id = body["id"].as_i64().unwrap();

        let (status, body) = send(
            db.clone(),
            "PUT",
            &format!("/books/{id}"),
            Some(json!({ "title": "New", "author": "Author", "year": 2024 })),
        )
        .await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(body["title"], "New");
        assert_eq!(body["year"], 2024);

        // Updating a missing book returns 404.
        let (status, _) = send(
            db,
            "PUT",
            "/books/9999",
            Some(json!({ "title": "X", "author": "Y" })),
        )
        .await;
        assert_eq!(status, StatusCode::NOT_FOUND);
    }

    #[tokio::test]
    async fn delete_book_removes_it() {
        let db = in_memory_db();
        let (_, body) = send(
            db.clone(),
            "POST",
            "/books",
            Some(json!({ "title": "Temp", "author": "Author" })),
        )
        .await;
        let id = body["id"].as_i64().unwrap();

        let (status, _) = send(db.clone(), "DELETE", &format!("/books/{id}"), None).await;
        assert_eq!(status, StatusCode::NO_CONTENT);

        let (status, _) = send(db.clone(), "GET", &format!("/books/{id}"), None).await;
        assert_eq!(status, StatusCode::NOT_FOUND);

        // Deleting again is a 404.
        let (status, _) = send(db, "DELETE", &format!("/books/{id}"), None).await;
        assert_eq!(status, StatusCode::NOT_FOUND);
    }

    #[tokio::test]
    async fn get_missing_book_is_404() {
        let db = in_memory_db();
        let (status, body) = send(db, "GET", "/books/42", None).await;
        assert_eq!(status, StatusCode::NOT_FOUND);
        assert_eq!(body["error"], "book not found");
    }
}
