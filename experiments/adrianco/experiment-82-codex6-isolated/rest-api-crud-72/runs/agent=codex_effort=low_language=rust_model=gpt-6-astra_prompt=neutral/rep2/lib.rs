use axum::{
    extract::{
        rejection::{JsonRejection, PathRejection, QueryRejection},
        Path, Query, State,
    },
    http::{header, StatusCode},
    response::{IntoResponse, Response},
    routing::get,
    Json, Router,
};
use rusqlite::{params, Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};

#[derive(Clone)]
struct Database(Arc<Mutex<Connection>>);

#[derive(Debug, Serialize, Deserialize)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct BookInput {
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

impl BookInput {
    fn validate(mut self) -> Result<Self, ApiError> {
        self.title = self.title.trim().to_owned();
        self.author = self.author.trim().to_owned();
        if self.title.is_empty() || self.author.is_empty() {
            return Err(ApiError(
                StatusCode::BAD_REQUEST,
                "title and author must not be blank".into(),
            ));
        }
        Ok(self)
    }
}

struct ApiError(StatusCode, String);
impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        (self.0, Json(serde_json::json!({"error": self.1}))).into_response()
    }
}
impl From<rusqlite::Error> for ApiError {
    fn from(error: rusqlite::Error) -> Self {
        eprintln!("Database error: {error}");
        internal_error()
    }
}
fn internal_error() -> ApiError {
    ApiError(
        StatusCode::INTERNAL_SERVER_ERROR,
        "internal server error".into(),
    )
}
fn not_found() -> ApiError {
    ApiError(StatusCode::NOT_FOUND, "book not found".into())
}
fn parse_id(id: Result<Path<i64>, PathRejection>) -> Result<i64, ApiError> {
    let Path(id) =
        id.map_err(|_| ApiError(StatusCode::BAD_REQUEST, "id must be an integer".into()))?;
    if id <= 0 {
        return Err(ApiError(
            StatusCode::BAD_REQUEST,
            "id must be positive".into(),
        ));
    }
    Ok(id)
}
fn parse_book(body: Result<Json<BookInput>, JsonRejection>) -> Result<BookInput, ApiError> {
    body.map_err(|err| {
        ApiError(
            if err.status() == StatusCode::UNPROCESSABLE_ENTITY {
                StatusCode::BAD_REQUEST
            } else {
                err.status()
            },
            err.body_text(),
        )
    })?
    .0
    .validate()
}

impl Database {
    async fn run<T: Send + 'static>(
        self,
        operation: impl FnOnce(&Connection) -> Result<T, ApiError> + Send + 'static,
    ) -> Result<T, ApiError> {
        tokio::task::spawn_blocking(move || {
            let connection = self.0.lock().map_err(|_| internal_error())?;
            operation(&connection)
        })
        .await
        .map_err(|_| internal_error())?
    }
}

/// Build the API over an existing SQLite connection, initializing its schema.
pub fn app(connection: Connection) -> rusqlite::Result<Router> {
    connection.busy_timeout(std::time::Duration::from_secs(5))?;
    connection.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL CHECK(length(trim(title)) > 0),
            author TEXT NOT NULL CHECK(length(trim(author)) > 0),
            year INTEGER,
            isbn TEXT
        );
        CREATE INDEX IF NOT EXISTS books_author ON books(author);",
    )?;
    Ok(Router::new()
        .route("/health", get(health))
        .route("/books", get(list_books).post(create_book))
        .route(
            "/books/{id}",
            get(get_book).put(update_book).delete(delete_book),
        )
        .fallback(|| async { ApiError(StatusCode::NOT_FOUND, "route not found".into()) })
        .method_not_allowed_fallback(|| async {
            ApiError(StatusCode::METHOD_NOT_ALLOWED, "method not allowed".into())
        })
        .with_state(Database(Arc::new(Mutex::new(connection)))))
}

async fn health(State(db): State<Database>) -> Result<Json<serde_json::Value>, ApiError> {
    db.run(|conn| {
        conn.query_row("SELECT 1", [], |_| Ok(()))?;
        Ok(())
    })
    .await?;
    Ok(Json(serde_json::json!({"status": "ok"})))
}
fn row_to_book(row: &rusqlite::Row<'_>) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}
fn find_book(conn: &Connection, id: i64) -> Result<Book, ApiError> {
    conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        [id],
        row_to_book,
    )
    .optional()?
    .ok_or_else(not_found)
}
async fn create_book(
    State(db): State<Database>,
    body: Result<Json<BookInput>, JsonRejection>,
) -> Result<Response, ApiError> {
    let book = parse_book(body)?;
    let book = db
        .run(move |conn| {
            conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
                params![book.title, book.author, book.year, book.isbn],
            )?;
            find_book(conn, conn.last_insert_rowid())
        })
        .await?;
    Ok((
        StatusCode::CREATED,
        [(header::LOCATION, format!("/books/{}", book.id))],
        Json(book),
    )
        .into_response())
}
#[derive(Deserialize)]
struct BookFilter {
    author: Option<String>,
}
async fn list_books(
    State(db): State<Database>,
    query: Result<Query<BookFilter>, QueryRejection>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let Query(filter) = query.map_err(|e| ApiError(StatusCode::BAD_REQUEST, e.body_text()))?;
    db.run(move |conn| {
        let mut statement = conn.prepare("SELECT id, title, author, year, isbn FROM books WHERE (?1 IS NULL OR author = ?1) ORDER BY id")?;
        let books = statement.query_map([filter.author], row_to_book)?.collect::<rusqlite::Result<Vec<_>>>()?;
        Ok(Json(books))
    }).await
}
async fn get_book(
    State(db): State<Database>,
    id: Result<Path<i64>, PathRejection>,
) -> Result<Json<Book>, ApiError> {
    let id = parse_id(id)?;
    db.run(move |conn| Ok(Json(find_book(conn, id)?))).await
}
async fn update_book(
    State(db): State<Database>,
    id: Result<Path<i64>, PathRejection>,
    body: Result<Json<BookInput>, JsonRejection>,
) -> Result<Json<Book>, ApiError> {
    let id = parse_id(id)?;
    let book = parse_book(body)?;
    db.run(move |conn| {
        let changed = conn.execute(
            "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
            params![book.title, book.author, book.year, book.isbn, id],
        )?;
        if changed == 0 {
            return Err(not_found());
        }
        Ok(Json(find_book(conn, id)?))
    })
    .await
}
async fn delete_book(
    State(db): State<Database>,
    id: Result<Path<i64>, PathRejection>,
) -> Result<StatusCode, ApiError> {
    let id = parse_id(id)?;
    db.run(move |conn| {
        if conn.execute("DELETE FROM books WHERE id = ?1", [id])? == 0 {
            return Err(not_found());
        }
        Ok(StatusCode::NO_CONTENT)
    })
    .await
}

#[cfg(test)]
mod tests;
