use axum::{
    extract::{rejection::JsonRejection, Path, Query, State},
    http::{header, StatusCode},
    response::{IntoResponse, Response},
    routing::get,
    Json, Router,
};
use rusqlite::{params, Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};

#[derive(Clone)]
pub struct Database(Arc<Mutex<Connection>>);

impl Database {
    pub fn open(path: impl AsRef<std::path::Path>) -> rusqlite::Result<Self> {
        Self::from_connection(Connection::open(path)?)
    }

    pub fn in_memory() -> rusqlite::Result<Self> {
        Self::from_connection(Connection::open_in_memory()?)
    }

    fn from_connection(connection: Connection) -> rusqlite::Result<Self> {
        connection.busy_timeout(std::time::Duration::from_secs(5))?;
        connection.execute_batch(
            "CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL CHECK(length(trim(title)) > 0),
                author TEXT NOT NULL CHECK(length(trim(author)) > 0),
                year INTEGER,
                isbn TEXT
            );",
        )?;
        Ok(Self(Arc::new(Mutex::new(connection))))
    }

    async fn run<T: Send + 'static>(
        &self,
        operation: impl FnOnce(&Connection) -> Result<T, ApiError> + Send + 'static,
    ) -> Result<T, ApiError> {
        let database = self.clone();
        tokio::task::spawn_blocking(move || {
            let connection = database.0.lock().map_err(|_| ApiError::internal())?;
            operation(&connection)
        })
        .await
        .map_err(|_| ApiError::internal())?
    }
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Deserialize)]
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
                "title and author are required".into(),
            ));
        }
        Ok(self)
    }
}

struct ApiError(StatusCode, String);
impl ApiError {
    fn internal() -> Self {
        Self(
            StatusCode::INTERNAL_SERVER_ERROR,
            "internal database error".into(),
        )
    }
    fn missing() -> Self {
        Self(StatusCode::NOT_FOUND, "book not found".into())
    }
}
impl From<rusqlite::Error> for ApiError {
    fn from(error: rusqlite::Error) -> Self {
        eprintln!("SQLite error: {error}");
        Self::internal()
    }
}
impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        (self.0, Json(serde_json::json!({"error": self.1}))).into_response()
    }
}

pub fn app(database: Database) -> Router {
    Router::new()
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
        .with_state(database)
}

async fn health(State(db): State<Database>) -> Result<Json<serde_json::Value>, ApiError> {
    db.run(|connection| {
        connection.query_row("SELECT 1", [], |_| Ok(()))?;
        Ok(())
    })
    .await?;
    Ok(Json(serde_json::json!({"status": "ok"})))
}

fn input(payload: Result<Json<BookInput>, JsonRejection>) -> Result<BookInput, ApiError> {
    payload
        .map_err(|error| ApiError(StatusCode::BAD_REQUEST, error.body_text()))?
        .0
        .validate()
}
fn id(value: String) -> Result<i64, ApiError> {
    value
        .parse::<i64>()
        .ok()
        .filter(|id| *id > 0)
        .ok_or_else(|| {
            ApiError(
                StatusCode::BAD_REQUEST,
                "id must be a positive integer".into(),
            )
        })
}
fn row_book(row: &rusqlite::Row<'_>) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}
fn find(connection: &Connection, id: i64) -> Result<Book, ApiError> {
    connection
        .query_row(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
            [id],
            row_book,
        )
        .optional()?
        .ok_or_else(ApiError::missing)
}
async fn create_book(
    State(db): State<Database>,
    payload: Result<Json<BookInput>, JsonRejection>,
) -> Result<impl IntoResponse, ApiError> {
    let book = input(payload)?;
    let book = db
        .run(move |connection| {
            connection.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
                params![book.title, book.author, book.year, book.isbn],
            )?;
            find(connection, connection.last_insert_rowid())
        })
        .await?;
    Ok((
        StatusCode::CREATED,
        [(header::LOCATION, format!("/books/{}", book.id))],
        Json(book),
    ))
}
#[derive(Deserialize)]
struct Filter {
    author: Option<String>,
}
async fn list_books(
    State(db): State<Database>,
    query: Result<Query<Filter>, axum::extract::rejection::QueryRejection>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let Query(filter) = query.map_err(|e| ApiError(StatusCode::BAD_REQUEST, e.body_text()))?;
    let books = db.run(move |connection| {
        let mut statement = connection.prepare("SELECT id, title, author, year, isbn FROM books WHERE (?1 IS NULL OR author = ?1) ORDER BY id")?;
        let books = statement.query_map([filter.author], row_book)?.collect::<rusqlite::Result<Vec<_>>>()?;
        Ok(books)
    }).await?;
    Ok(Json(books))
}
async fn get_book(
    State(db): State<Database>,
    Path(value): Path<String>,
) -> Result<Json<Book>, ApiError> {
    let id = id(value)?;
    Ok(Json(db.run(move |connection| find(connection, id)).await?))
}
async fn update_book(
    State(db): State<Database>,
    Path(value): Path<String>,
    payload: Result<Json<BookInput>, JsonRejection>,
) -> Result<Json<Book>, ApiError> {
    let id = id(value)?;
    let book = input(payload)?;
    Ok(Json(
        db.run(move |connection| {
            if connection.execute(
                "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
                params![book.title, book.author, book.year, book.isbn, id],
            )? == 0
            {
                return Err(ApiError::missing());
            }
            find(connection, id)
        })
        .await?,
    ))
}
async fn delete_book(
    State(db): State<Database>,
    Path(value): Path<String>,
) -> Result<Json<serde_json::Value>, ApiError> {
    let id = id(value)?;
    db.run(move |connection| {
        if connection.execute("DELETE FROM books WHERE id = ?1", [id])? == 0 {
            return Err(ApiError::missing());
        }
        Ok(())
    })
    .await?;
    Ok(Json(serde_json::json!({"deleted": id})))
}

#[cfg(test)]
mod tests;
