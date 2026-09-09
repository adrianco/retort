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
        F: FnOnce(&Connection) -> rusqlite::Result<T> + Send + 'static,
    {
        let db = self.0.clone();
        tokio::task::spawn_blocking(move || {
            let connection = db.lock().map_err(|_| ApiError::internal())?;
            operation(&connection).map_err(|error| {
                eprintln!("database error: {error}");
                ApiError::internal()
            })
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
            "internal server error".into(),
        )
    }
    fn missing() -> Self {
        Self(StatusCode::NOT_FOUND, "book not found".into())
    }
}
impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        (self.0, Json(serde_json::json!({"error": self.1}))).into_response()
    }
}

fn input(body: Result<Json<BookInput>, JsonRejection>) -> Result<BookInput, ApiError> {
    body.map_err(|e| {
        ApiError(
            if e.status() == StatusCode::UNSUPPORTED_MEDIA_TYPE
                || e.status() == StatusCode::PAYLOAD_TOO_LARGE
            {
                e.status()
            } else {
                StatusCode::BAD_REQUEST
            },
            e.body_text(),
        )
    })?
    .0
    .validate()
}
fn id(raw: String) -> Result<i64, ApiError> {
    raw.parse::<i64>().ok().filter(|n| *n > 0).ok_or_else(|| {
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

pub fn app(db: Database) -> Router {
    Router::new()
        .route(
            "/health",
            get(|| async { Json(serde_json::json!({"status": "ok"})) }),
        )
        .route("/books", get(list).post(create))
        .route("/books/{id}", get(read).put(update).delete(delete))
        .fallback(|| async { ApiError(StatusCode::NOT_FOUND, "route not found".into()) })
        .method_not_allowed_fallback(|| async {
            ApiError(StatusCode::METHOD_NOT_ALLOWED, "method not allowed".into())
        })
        .with_state(db)
}

async fn create(
    State(db): State<Database>,
    body: Result<Json<BookInput>, JsonRejection>,
) -> Result<Response, ApiError> {
    let b = input(body)?;
    let book = db
        .run(move |c| {
            c.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
                params![b.title, b.author, b.year, b.isbn],
            )?;
            Ok(Book {
                id: c.last_insert_rowid(),
                title: b.title,
                author: b.author,
                year: b.year,
                isbn: b.isbn,
            })
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
struct Filter {
    author: Option<String>,
}
async fn list(
    State(db): State<Database>,
    query: Result<Query<Filter>, axum::extract::rejection::QueryRejection>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let filter = query
        .map_err(|e| ApiError(StatusCode::BAD_REQUEST, e.body_text()))?
        .0;
    db.run(move |c| {
        let mut statement = c.prepare("SELECT id, title, author, year, isbn FROM books WHERE (?1 IS NULL OR author = ?1) ORDER BY id")?;
        let books = statement.query_map(params![filter.author], row_book)?.collect::<rusqlite::Result<Vec<_>>>()?;
        Ok(books)
    }).await.map(Json)
}
async fn read(State(db): State<Database>, Path(raw): Path<String>) -> Result<Json<Book>, ApiError> {
    let id = id(raw)?;
    db.run(move |c| {
        c.query_row(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
            [id],
            row_book,
        )
        .optional()
    })
    .await?
    .map(Json)
    .ok_or_else(ApiError::missing)
}
async fn update(
    State(db): State<Database>,
    Path(raw): Path<String>,
    body: Result<Json<BookInput>, JsonRejection>,
) -> Result<Json<Book>, ApiError> {
    let id = id(raw)?;
    let b = input(body)?;
    db.run(move |c| {
        let changed = c.execute(
            "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
            params![b.title, b.author, b.year, b.isbn, id],
        )?;
        Ok((changed > 0).then_some(Book {
            id,
            title: b.title,
            author: b.author,
            year: b.year,
            isbn: b.isbn,
        }))
    })
    .await?
    .map(Json)
    .ok_or_else(ApiError::missing)
}
async fn delete(
    State(db): State<Database>,
    Path(raw): Path<String>,
) -> Result<Json<serde_json::Value>, ApiError> {
    let id = id(raw)?;
    let changed = db
        .run(move |c| c.execute("DELETE FROM books WHERE id = ?1", [id]))
        .await?;
    if changed == 0 {
        return Err(ApiError::missing());
    }
    Ok(Json(serde_json::json!({"deleted": id})))
}
