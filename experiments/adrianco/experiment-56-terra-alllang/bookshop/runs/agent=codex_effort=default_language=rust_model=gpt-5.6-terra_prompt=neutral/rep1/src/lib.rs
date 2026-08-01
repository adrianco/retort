use std::sync::{Arc, Mutex};

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::IntoResponse,
    routing::{delete, get, post, put},
    Json, Router,
};
use rusqlite::{params, Connection, OptionalExtension};
use serde::{Deserialize, Serialize};

#[derive(Clone)]
pub struct AppState {
    db: Arc<Mutex<Connection>>,
}

impl AppState {
    pub fn new(database_url: &str) -> Result<Self, rusqlite::Error> {
        let connection = Connection::open(database_url)?;
        connection.execute_batch(
            "CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT
            );",
        )?;
        Ok(Self {
            db: Arc::new(Mutex::new(connection)),
        })
    }

    pub fn in_memory() -> Result<Self, rusqlite::Error> {
        Self::new(":memory:")
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

#[derive(Debug, Deserialize)]
pub struct BookInput {
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
struct ListParams {
    author: Option<String>,
}

#[derive(Debug, Serialize)]
struct ErrorResponse {
    error: String,
}

type ApiResult<T> = Result<T, (StatusCode, Json<ErrorResponse>)>;

pub fn app(state: AppState) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book).get(list_books))
        .route(
            "/books/:id",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(state)
}

async fn health() -> &'static str {
    "ok"
}

async fn create_book(
    State(state): State<AppState>,
    Json(input): Json<BookInput>,
) -> ApiResult<impl IntoResponse> {
    validate(&input)?;
    let db = state.db.lock().map_err(internal_error)?;
    db.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![
            input.title.trim(),
            input.author.trim(),
            input.year,
            input.isbn
        ],
    )
    .map_err(internal_error)?;
    let book = book_by_id(&db, db.last_insert_rowid())
        .map_err(internal_error)?
        .expect("inserted book must exist");
    Ok((StatusCode::CREATED, Json(book)))
}

async fn list_books(
    State(state): State<AppState>,
    Query(query): Query<ListParams>,
) -> ApiResult<Json<Vec<Book>>> {
    let db = state.db.lock().map_err(internal_error)?;
    let mut books = Vec::new();
    if let Some(author) = query.author {
        let mut statement = db
            .prepare(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ?1 ORDER BY id",
            )
            .map_err(internal_error)?;
        let rows = statement
            .query_map([author], row_to_book)
            .map_err(internal_error)?;
        for row in rows {
            books.push(row.map_err(internal_error)?);
        }
    } else {
        let mut statement = db
            .prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")
            .map_err(internal_error)?;
        let rows = statement
            .query_map([], row_to_book)
            .map_err(internal_error)?;
        for row in rows {
            books.push(row.map_err(internal_error)?);
        }
    }
    Ok(Json(books))
}

async fn get_book(State(state): State<AppState>, Path(id): Path<i64>) -> ApiResult<Json<Book>> {
    let db = state.db.lock().map_err(internal_error)?;
    match book_by_id(&db, id).map_err(internal_error)? {
        Some(book) => Ok(Json(book)),
        None => Err(not_found()),
    }
}

async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Json(input): Json<BookInput>,
) -> ApiResult<Json<Book>> {
    validate(&input)?;
    let db = state.db.lock().map_err(internal_error)?;
    let changed = db
        .execute(
            "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
            params![
                input.title.trim(),
                input.author.trim(),
                input.year,
                input.isbn,
                id
            ],
        )
        .map_err(internal_error)?;
    if changed == 0 {
        return Err(not_found());
    }
    Ok(Json(
        book_by_id(&db, id)
            .map_err(internal_error)?
            .expect("updated book must exist"),
    ))
}

async fn delete_book(State(state): State<AppState>, Path(id): Path<i64>) -> ApiResult<StatusCode> {
    let db = state.db.lock().map_err(internal_error)?;
    let changed = db
        .execute("DELETE FROM books WHERE id = ?1", [id])
        .map_err(internal_error)?;
    if changed == 0 {
        Err(not_found())
    } else {
        Ok(StatusCode::NO_CONTENT)
    }
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

fn book_by_id(db: &Connection, id: i64) -> rusqlite::Result<Option<Book>> {
    db.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        [id],
        row_to_book,
    )
    .optional()
}

fn validate(input: &BookInput) -> ApiResult<()> {
    if input.title.trim().is_empty() || input.author.trim().is_empty() {
        Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse {
                error: "title and author are required".to_owned(),
            }),
        ))
    } else {
        Ok(())
    }
}

fn not_found() -> (StatusCode, Json<ErrorResponse>) {
    (
        StatusCode::NOT_FOUND,
        Json(ErrorResponse {
            error: "book not found".to_owned(),
        }),
    )
}

fn internal_error<E: std::fmt::Display>(error: E) -> (StatusCode, Json<ErrorResponse>) {
    (
        StatusCode::INTERNAL_SERVER_ERROR,
        Json(ErrorResponse {
            error: error.to_string(),
        }),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{
        body::Body,
        http::{Request, StatusCode},
    };
    use tower::ServiceExt;

    fn test_app() -> Router {
        app(AppState::in_memory().unwrap())
    }
    fn request(method: &str, uri: &str, body: &str) -> Request<Body> {
        Request::builder()
            .method(method)
            .uri(uri)
            .header("content-type", "application/json")
            .body(Body::from(body.to_owned()))
            .unwrap()
    }

    #[tokio::test]
    async fn creates_and_retrieves_a_book() {
        let app = test_app();
        let response = app
            .clone()
            .oneshot(request(
                "POST",
                "/books",
                r#"{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}"#,
            ))
            .await
            .unwrap();
        assert_eq!(response.status(), StatusCode::CREATED);
        let response = app.oneshot(request("GET", "/books/1", "")).await.unwrap();
        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn filters_books_by_author() {
        let app = test_app();
        app.clone()
            .oneshot(request(
                "POST",
                "/books",
                r#"{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":null}"#,
            ))
            .await
            .unwrap();
        app.clone()
            .oneshot(request(
                "POST",
                "/books",
                r#"{"title":"Foundation","author":"Isaac Asimov","year":1951,"isbn":null}"#,
            ))
            .await
            .unwrap();
        let response = app
            .oneshot(request("GET", "/books?author=Frank%20Herbert", ""))
            .await
            .unwrap();
        assert_eq!(response.status(), StatusCode::OK);
        let bytes = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .unwrap();
        let books: Vec<Book> = serde_json::from_slice(&bytes).unwrap();
        assert_eq!(books.len(), 1);
        assert_eq!(books[0].title, "Dune");
    }

    #[tokio::test]
    async fn rejects_books_without_required_fields() {
        let response = test_app()
            .oneshot(request(
                "POST",
                "/books",
                r#"{"title":" ","author":"","year":null,"isbn":null}"#,
            ))
            .await
            .unwrap();
        assert_eq!(response.status(), StatusCode::BAD_REQUEST);
    }

    #[tokio::test]
    async fn updates_and_deletes_a_book() {
        let app = test_app();
        app.clone()
            .oneshot(request(
                "POST",
                "/books",
                r#"{"title":"Old","author":"A","year":null,"isbn":null}"#,
            ))
            .await
            .unwrap();
        let response = app
            .clone()
            .oneshot(request(
                "PUT",
                "/books/1",
                r#"{"title":"New","author":"A","year":2020,"isbn":"x"}"#,
            ))
            .await
            .unwrap();
        assert_eq!(response.status(), StatusCode::OK);
        let response = app
            .clone()
            .oneshot(request("DELETE", "/books/1", ""))
            .await
            .unwrap();
        assert_eq!(response.status(), StatusCode::NO_CONTENT);
        let response = app.oneshot(request("GET", "/books/1", "")).await.unwrap();
        assert_eq!(response.status(), StatusCode::NOT_FOUND);
    }
}
