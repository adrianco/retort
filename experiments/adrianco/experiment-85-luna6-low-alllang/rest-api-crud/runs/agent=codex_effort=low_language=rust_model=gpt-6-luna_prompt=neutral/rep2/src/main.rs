use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::get,
    Json, Router,
};
use rusqlite::{params, Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use std::{collections::HashMap, net::SocketAddr, sync::{Arc, Mutex}};

#[derive(Clone)]
struct AppState(Arc<Mutex<Connection>>);

#[derive(Debug, Serialize, Deserialize, PartialEq, Eq)]
struct Book {
    id: i64,
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Deserialize)]
struct BookInput {
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Serialize)]
struct ApiError { error: String }

struct HttpError(StatusCode, String);
impl IntoResponse for HttpError {
    fn into_response(self) -> Response {
        (self.0, Json(ApiError { error: self.1 })).into_response()
    }
}

fn db_error(_: rusqlite::Error) -> HttpError {
    HttpError(StatusCode::INTERNAL_SERVER_ERROR, "database error".into())
}

fn validate(input: &BookInput) -> Result<(), HttpError> {
    if input.title.trim().is_empty() || input.author.trim().is_empty() {
        return Err(HttpError(StatusCode::BAD_REQUEST, "title and author are required".into()));
    }
    Ok(())
}

pub fn app() -> Router {
    let conn = Connection::open("books.db").expect("open books.db");
    build_app(conn).expect("initialize database")
}

fn build_app(conn: Connection) -> rusqlite::Result<Router> {
    conn.execute_batch("PRAGMA foreign_keys=ON; CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT
    );")?;
    let state = AppState(Arc::new(Mutex::new(conn)));
    Ok(Router::new()
        .route("/health", get(|| async { (StatusCode::OK, Json(serde_json::json!({"status":"ok"}))) }))
        .route("/books", get(list_books).post(create_book))
        .route("/books/{id}", get(get_book).put(update_book).delete(delete_book))
        .with_state(state))
}

async fn create_book(State(state): State<AppState>, Json(input): Json<BookInput>) -> Result<impl IntoResponse, HttpError> {
    validate(&input)?;
    let conn = state.0.lock().unwrap();
    conn.execute("INSERT INTO books (title,author,year,isbn) VALUES (?1,?2,?3,?4)",
        params![input.title.trim(), input.author.trim(), input.year, input.isbn]) .map_err(db_error)?;
    let id = conn.last_insert_rowid();
    let book = conn.query_row("SELECT id,title,author,year,isbn FROM books WHERE id=?1", [id], row_book).map_err(db_error)?;
    Ok((StatusCode::CREATED, Json(book)))
}

async fn list_books(State(state): State<AppState>, Query(query): Query<HashMap<String, String>>) -> Result<Json<Vec<Book>>, HttpError> {
    let conn = state.0.lock().unwrap();
    let mut stmt = if query.contains_key("author") {
        conn.prepare("SELECT id,title,author,year,isbn FROM books WHERE author=?1 ORDER BY id").map_err(db_error)?
    } else {
        conn.prepare("SELECT id,title,author,year,isbn FROM books ORDER BY id").map_err(db_error)?
    };
    let rows = if let Some(author) = query.get("author") {
        stmt.query_map([author], row_book).map_err(db_error)?
    } else {
        stmt.query_map([], row_book).map_err(db_error)?
    };
    let books = rows.collect::<rusqlite::Result<Vec<_>>>().map_err(db_error)?;
    Ok(Json(books))
}

async fn get_book(State(state): State<AppState>, Path(id): Path<i64>) -> Result<Json<Book>, HttpError> {
    let conn = state.0.lock().unwrap();
    let book = conn.query_row("SELECT id,title,author,year,isbn FROM books WHERE id=?1", [id], row_book)
        .optional().map_err(db_error)?.ok_or_else(not_found)?;
    Ok(Json(book))
}

async fn update_book(State(state): State<AppState>, Path(id): Path<i64>, Json(input): Json<BookInput>) -> Result<Json<Book>, HttpError> {
    validate(&input)?;
    let conn = state.0.lock().unwrap();
    let changed = conn.execute("UPDATE books SET title=?1,author=?2,year=?3,isbn=?4 WHERE id=?5",
        params![input.title.trim(), input.author.trim(), input.year, input.isbn, id]).map_err(db_error)?;
    if changed == 0 { return Err(not_found()); }
    let book = conn.query_row("SELECT id,title,author,year,isbn FROM books WHERE id=?1", [id], row_book).map_err(db_error)?;
    Ok(Json(book))
}

async fn delete_book(State(state): State<AppState>, Path(id): Path<i64>) -> Result<StatusCode, HttpError> {
    let conn = state.0.lock().unwrap();
    let changed = conn.execute("DELETE FROM books WHERE id=?1", [id]).map_err(db_error)?;
    if changed == 0 { return Err(not_found()); }
    Ok(StatusCode::NO_CONTENT)
}

fn row_book(row: &rusqlite::Row<'_>) -> rusqlite::Result<Book> {
    Ok(Book { id: row.get(0)?, title: row.get(1)?, author: row.get(2)?, year: row.get(3)?, isbn: row.get(4)? })
}
fn not_found() -> HttpError { HttpError(StatusCode::NOT_FOUND, "book not found".into()) }

#[tokio::main]
async fn main() {
    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await.expect("bind port 3000");
    let addr: SocketAddr = listener.local_addr().unwrap();
    println!("Book API listening on {addr}");
    axum::serve(listener, app()).await.expect("serve API");
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{body::{to_bytes, Body}, http::{Request, StatusCode}};
    use tower::ServiceExt;

    fn test_app() -> Router { build_app(Connection::open_in_memory().unwrap()).unwrap() }
    async fn call(app: Router, method: &str, uri: &str, body: Option<&str>) -> axum::response::Response {
        let mut req = Request::builder().method(method).uri(uri);
        if body.is_some() { req = req.header("content-type", "application/json"); }
        app.oneshot(req.body(Body::from(body.unwrap_or("").to_owned())).unwrap()).await.unwrap()
    }
    async fn json(response: axum::response::Response) -> serde_json::Value {
        serde_json::from_slice(&to_bytes(response.into_body(), usize::MAX).await.unwrap()).unwrap()
    }

    #[tokio::test]
    async fn creates_lists_and_filters_books() {
        let app = test_app();
        let created = call(app.clone(), "POST", "/books", Some(r#"{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}"#)).await;
        assert_eq!(created.status(), StatusCode::CREATED);
        let data = json(created).await;
        assert_eq!(data["id"], 1);
        let all = json(call(app.clone(), "GET", "/books", None).await).await;
        assert_eq!(all.as_array().unwrap().len(), 1);
        let filtered = json(call(app, "GET", "/books?author=Nobody", None).await).await;
        assert_eq!(filtered.as_array().unwrap().len(), 0);
    }

    #[tokio::test]
    async fn validates_required_fields_and_returns_not_found() {
        let app = test_app();
        let invalid = call(app.clone(), "POST", "/books", Some(r#"{"title":" ","author":"A"}"#)).await;
        assert_eq!(invalid.status(), StatusCode::BAD_REQUEST);
        let absent = call(app, "GET", "/books/99", None).await;
        assert_eq!(absent.status(), StatusCode::NOT_FOUND);
    }

    #[tokio::test]
    async fn updates_and_deletes_books() {
        let app = test_app();
        let created = call(app.clone(), "POST", "/books", Some(r#"{"title":"Old","author":"A"}"#)).await;
        assert_eq!(created.status(), StatusCode::CREATED);
        let updated = call(app.clone(), "PUT", "/books/1", Some(r#"{"title":"New","author":"B","year":2020}"#)).await;
        assert_eq!(updated.status(), StatusCode::OK);
        assert_eq!(json(updated).await["title"], "New");
        assert_eq!(call(app.clone(), "DELETE", "/books/1", None).await.status(), StatusCode::NO_CONTENT);
        assert_eq!(call(app, "GET", "/books/1", None).await.status(), StatusCode::NOT_FOUND);
    }

    #[tokio::test]
    async fn health_endpoint_is_json() {
        let response = call(test_app(), "GET", "/health", None).await;
        assert_eq!(response.status(), StatusCode::OK);
        assert_eq!(json(response).await["status"], "ok");
    }
}
