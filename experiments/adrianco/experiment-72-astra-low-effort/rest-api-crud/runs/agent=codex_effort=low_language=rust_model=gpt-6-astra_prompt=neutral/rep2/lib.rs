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
pub struct Database(Arc<Mutex<Connection>>);

impl Database {
    pub fn open(path: impl AsRef<std::path::Path>) -> rusqlite::Result<Self> {
        Self::from_connection(Connection::open(path)?)
    }

    pub fn from_connection(connection: Connection) -> rusqlite::Result<Self> {
        connection.busy_timeout(std::time::Duration::from_secs(5))?;
        connection.execute_batch(
            "CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL CHECK(length(trim(title)) > 0),
                author TEXT NOT NULL CHECK(length(trim(author)) > 0),
                year INTEGER,
                isbn TEXT
            ); CREATE INDEX IF NOT EXISTS books_author ON books(author);",
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

#[derive(Debug, Serialize, Deserialize, PartialEq)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Deserialize)]
pub struct BookInput {
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
            return Err(ApiError::bad_request("title and author must not be blank"));
        }
        Ok(self)
    }
}

pub struct ApiError(StatusCode, String);
impl ApiError {
    fn bad_request(message: impl Into<String>) -> Self {
        Self(StatusCode::BAD_REQUEST, message.into())
    }
    fn internal() -> Self {
        Self(
            StatusCode::INTERNAL_SERVER_ERROR,
            "internal server error".into(),
        )
    }
    fn not_found() -> Self {
        Self(StatusCode::NOT_FOUND, "book not found".into())
    }
}
impl From<rusqlite::Error> for ApiError {
    fn from(error: rusqlite::Error) -> Self {
        eprintln!("database error: {error}");
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
    db.run(|conn| {
        conn.query_row("SELECT 1", [], |_| Ok(()))?;
        Ok(())
    })
    .await?;
    Ok(Json(serde_json::json!({"status": "ok"})))
}

fn input(payload: Result<Json<BookInput>, JsonRejection>) -> Result<BookInput, ApiError> {
    payload
        .map_err(|e| ApiError(e.status(), e.body_text()))?
        .0
        .validate()
}
fn id(path: Result<Path<i64>, PathRejection>) -> Result<i64, ApiError> {
    let id = path
        .map_err(|_| ApiError::bad_request("id must be a positive integer"))?
        .0;
    if id <= 0 {
        return Err(ApiError::bad_request("id must be a positive integer"));
    }
    Ok(id)
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
fn find(conn: &Connection, id: i64) -> Result<Book, ApiError> {
    conn.query_row(
        "SELECT id,title,author,year,isbn FROM books WHERE id=?1",
        [id],
        row_book,
    )
    .optional()?
    .ok_or_else(ApiError::not_found)
}

async fn create_book(
    State(db): State<Database>,
    payload: Result<Json<BookInput>, JsonRejection>,
) -> Result<Response, ApiError> {
    let book = input(payload)?;
    let book = db
        .run(move |conn| {
            conn.execute(
                "INSERT INTO books(title,author,year,isbn) VALUES (?1,?2,?3,?4)",
                params![book.title, book.author, book.year, book.isbn],
            )?;
            find(conn, conn.last_insert_rowid())
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
async fn list_books(
    State(db): State<Database>,
    query: Result<Query<Filter>, QueryRejection>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let filter = query.map_err(|e| ApiError::bad_request(e.body_text()))?.0;
    Ok(Json(
        db.run(move |conn| {
            let (sql, parameters) = match &filter.author {
                Some(author) => (
                    "SELECT id,title,author,year,isbn FROM books WHERE author=?1 ORDER BY id",
                    vec![author.as_str()],
                ),
                None => (
                    "SELECT id,title,author,year,isbn FROM books ORDER BY id",
                    vec![],
                ),
            };
            let mut statement = conn.prepare(sql)?;
            let books = statement
                .query_map(rusqlite::params_from_iter(parameters), row_book)?
                .collect::<rusqlite::Result<Vec<_>>>()?;
            Ok(books)
        })
        .await?,
    ))
}
async fn get_book(
    State(db): State<Database>,
    path: Result<Path<i64>, PathRejection>,
) -> Result<Json<Book>, ApiError> {
    let id = id(path)?;
    Ok(Json(db.run(move |conn| find(conn, id)).await?))
}
async fn update_book(
    State(db): State<Database>,
    path: Result<Path<i64>, PathRejection>,
    payload: Result<Json<BookInput>, JsonRejection>,
) -> Result<Json<Book>, ApiError> {
    let id = id(path)?;
    let book = input(payload)?;
    Ok(Json(
        db.run(move |conn| {
            if conn.execute(
                "UPDATE books SET title=?1,author=?2,year=?3,isbn=?4 WHERE id=?5",
                params![book.title, book.author, book.year, book.isbn, id],
            )? == 0
            {
                return Err(ApiError::not_found());
            }
            find(conn, id)
        })
        .await?,
    ))
}
async fn delete_book(
    State(db): State<Database>,
    path: Result<Path<i64>, PathRejection>,
) -> Result<StatusCode, ApiError> {
    let id = id(path)?;
    db.run(move |conn| {
        if conn.execute("DELETE FROM books WHERE id=?1", [id])? == 0 {
            return Err(ApiError::not_found());
        }
        Ok(())
    })
    .await?;
    Ok(StatusCode::NO_CONTENT)
}
