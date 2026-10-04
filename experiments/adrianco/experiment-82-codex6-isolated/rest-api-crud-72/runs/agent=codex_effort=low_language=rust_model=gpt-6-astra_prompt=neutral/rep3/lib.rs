use axum::{
    extract::{
        rejection::{JsonRejection, PathRejection, QueryRejection},
        Path, Query, State,
    },
    http::StatusCode,
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
    pub fn open(path: &str) -> rusqlite::Result<Self> {
        let connection = Connection::open(path)?;
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

    async fn run<T, F>(&self, operation: F) -> Result<T, ApiError>
    where
        T: Send + 'static,
        F: FnOnce(&Connection) -> Result<T, ApiError> + Send + 'static,
    {
        let db = self.0.clone();
        tokio::task::spawn_blocking(move || {
            let connection = db.lock().map_err(|_| ApiError::internal())?;
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
                "title and author must not be blank".into(),
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
            "internal server error".into(),
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
        .route("/books", get(list).post(create))
        .route("/books/{id}", get(fetch).put(update).delete(remove))
        .fallback(|| async { ApiError(StatusCode::NOT_FOUND, "route not found".into()) })
        .method_not_allowed_fallback(|| async {
            ApiError(StatusCode::METHOD_NOT_ALLOWED, "method not allowed".into())
        })
        .with_state(database)
}

async fn health(State(db): State<Database>) -> Result<Json<serde_json::Value>, ApiError> {
    db.run(|c| {
        c.query_row("SELECT 1", [], |_| Ok(()))?;
        Ok(())
    })
    .await?;
    Ok(Json(serde_json::json!({"status": "ok"})))
}

fn input(value: Result<Json<BookInput>, JsonRejection>) -> Result<BookInput, ApiError> {
    value
        .map_err(|e| ApiError(StatusCode::BAD_REQUEST, e.body_text()))?
        .0
        .validate()
}
fn id(value: Result<Path<i64>, PathRejection>) -> Result<i64, ApiError> {
    let id = value
        .map_err(|_| {
            ApiError(
                StatusCode::BAD_REQUEST,
                "id must be a positive integer".into(),
            )
        })?
        .0;
    if id <= 0 {
        return Err(ApiError(
            StatusCode::BAD_REQUEST,
            "id must be a positive integer".into(),
        ));
    }
    Ok(id)
}
fn row(row: &rusqlite::Row<'_>) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}
fn get_book(c: &Connection, id: i64) -> Result<Book, ApiError> {
    c.query_row(
        "SELECT id,title,author,year,isbn FROM books WHERE id=?1",
        [id],
        row,
    )
    .optional()?
    .ok_or_else(ApiError::missing)
}
async fn create(
    State(db): State<Database>,
    body: Result<Json<BookInput>, JsonRejection>,
) -> Result<impl IntoResponse, ApiError> {
    let book = input(body)?;
    let book = db
        .run(move |c| {
            c.execute(
                "INSERT INTO books(title,author,year,isbn) VALUES (?1,?2,?3,?4)",
                params![book.title, book.author, book.year, book.isbn],
            )?;
            get_book(c, c.last_insert_rowid())
        })
        .await?;
    Ok((
        StatusCode::CREATED,
        [("location", format!("/books/{}", book.id))],
        Json(book),
    ))
}
#[derive(Deserialize)]
struct Filter {
    author: Option<String>,
}
async fn list(
    State(db): State<Database>,
    filter: Result<Query<Filter>, QueryRejection>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let filter = filter
        .map_err(|e| ApiError(StatusCode::BAD_REQUEST, e.body_text()))?
        .0;
    db.run(move |c| {
        let mut stmt = c.prepare("SELECT id,title,author,year,isbn FROM books WHERE (?1 IS NULL OR author=?1) ORDER BY id")?;
        let books = stmt.query_map([filter.author], row)?.collect::<rusqlite::Result<Vec<_>>>()?;
        Ok(Json(books))
    }).await
}
async fn fetch(
    State(db): State<Database>,
    path: Result<Path<i64>, PathRejection>,
) -> Result<Json<Book>, ApiError> {
    let id = id(path)?;
    db.run(move |c| Ok(Json(get_book(c, id)?))).await
}
async fn update(
    State(db): State<Database>,
    path: Result<Path<i64>, PathRejection>,
    body: Result<Json<BookInput>, JsonRejection>,
) -> Result<Json<Book>, ApiError> {
    let id = id(path)?;
    let book = input(body)?;
    db.run(move |c| {
        if c.execute(
            "UPDATE books SET title=?1,author=?2,year=?3,isbn=?4 WHERE id=?5",
            params![book.title, book.author, book.year, book.isbn, id],
        )? == 0
        {
            return Err(ApiError::missing());
        }
        Ok(Json(get_book(c, id)?))
    })
    .await
}
async fn remove(
    State(db): State<Database>,
    path: Result<Path<i64>, PathRejection>,
) -> Result<StatusCode, ApiError> {
    let id = id(path)?;
    db.run(move |c| {
        if c.execute("DELETE FROM books WHERE id=?1", [id])? == 0 {
            return Err(ApiError::missing());
        }
        Ok(StatusCode::NO_CONTENT)
    })
    .await
}

#[cfg(test)]
mod tests;
