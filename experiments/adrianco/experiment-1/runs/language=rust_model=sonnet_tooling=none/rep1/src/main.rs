use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::Json,
    routing::{get, post},
    Router,
};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};
use uuid::Uuid;

type Db = Arc<Mutex<Connection>>;

// ── Models ────────────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Book {
    pub id: String,
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct CreateBook {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct UpdateBook {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

// ── DB helpers ────────────────────────────────────────────────────────────────

pub fn init_db(conn: &Connection) {
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id     TEXT PRIMARY KEY,
            title  TEXT NOT NULL,
            author TEXT NOT NULL,
            year   INTEGER,
            isbn   TEXT
        );",
    )
    .expect("failed to initialise database");
}

// ── Handlers ──────────────────────────────────────────────────────────────────

async fn health() -> Json<serde_json::Value> {
    Json(serde_json::json!({ "status": "ok" }))
}

async fn create_book(
    State(db): State<Db>,
    Json(payload): Json<CreateBook>,
) -> (StatusCode, Json<serde_json::Value>) {
    let title = match payload.title.filter(|s| !s.trim().is_empty()) {
        Some(t) => t,
        None => {
            return (
                StatusCode::UNPROCESSABLE_ENTITY,
                Json(serde_json::json!({ "error": "title is required" })),
            )
        }
    };
    let author = match payload.author.filter(|s| !s.trim().is_empty()) {
        Some(a) => a,
        None => {
            return (
                StatusCode::UNPROCESSABLE_ENTITY,
                Json(serde_json::json!({ "error": "author is required" })),
            )
        }
    };

    let id = Uuid::new_v4().to_string();
    let book = Book {
        id: id.clone(),
        title,
        author,
        year: payload.year,
        isbn: payload.isbn,
    };

    let conn = db.lock().unwrap();
    conn.execute(
        "INSERT INTO books (id, title, author, year, isbn) VALUES (?1, ?2, ?3, ?4, ?5)",
        params![book.id, book.title, book.author, book.year, book.isbn],
    )
    .unwrap();

    (StatusCode::CREATED, Json(serde_json::to_value(&book).unwrap()))
}

async fn list_books(
    State(db): State<Db>,
    Query(query): Query<ListQuery>,
) -> Json<serde_json::Value> {
    let conn = db.lock().unwrap();

    let books: Vec<Book> = if let Some(author_filter) = query.author {
        let mut stmt = conn
            .prepare("SELECT id, title, author, year, isbn FROM books WHERE author LIKE ?1")
            .unwrap();
        let pattern = format!("%{}%", author_filter);
        stmt.query_map(params![pattern], row_to_book)
            .unwrap()
            .filter_map(|r| r.ok())
            .collect()
    } else {
        let mut stmt = conn
            .prepare("SELECT id, title, author, year, isbn FROM books")
            .unwrap();
        stmt.query_map([], row_to_book)
            .unwrap()
            .filter_map(|r| r.ok())
            .collect()
    };

    Json(serde_json::to_value(books).unwrap())
}

async fn get_book(
    State(db): State<Db>,
    Path(id): Path<String>,
) -> (StatusCode, Json<serde_json::Value>) {
    let conn = db.lock().unwrap();
    let result = conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        params![id],
        row_to_book,
    );
    match result {
        Ok(book) => (StatusCode::OK, Json(serde_json::to_value(&book).unwrap())),
        Err(rusqlite::Error::QueryReturnedNoRows) => (
            StatusCode::NOT_FOUND,
            Json(serde_json::json!({ "error": "book not found" })),
        ),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(serde_json::json!({ "error": e.to_string() })),
        ),
    }
}

async fn update_book(
    State(db): State<Db>,
    Path(id): Path<String>,
    Json(payload): Json<UpdateBook>,
) -> (StatusCode, Json<serde_json::Value>) {
    let conn = db.lock().unwrap();

    // Fetch existing book first
    let existing = conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        params![id],
        row_to_book,
    );
    let existing = match existing {
        Ok(b) => b,
        Err(rusqlite::Error::QueryReturnedNoRows) => {
            return (
                StatusCode::NOT_FOUND,
                Json(serde_json::json!({ "error": "book not found" })),
            )
        }
        Err(e) => {
            return (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(serde_json::json!({ "error": e.to_string() })),
            )
        }
    };

    // Validate required fields if provided
    if let Some(ref t) = payload.title {
        if t.trim().is_empty() {
            return (
                StatusCode::UNPROCESSABLE_ENTITY,
                Json(serde_json::json!({ "error": "title cannot be empty" })),
            );
        }
    }
    if let Some(ref a) = payload.author {
        if a.trim().is_empty() {
            return (
                StatusCode::UNPROCESSABLE_ENTITY,
                Json(serde_json::json!({ "error": "author cannot be empty" })),
            );
        }
    }

    let updated = Book {
        id: existing.id,
        title: payload.title.unwrap_or(existing.title),
        author: payload.author.unwrap_or(existing.author),
        year: payload.year.or(existing.year),
        isbn: payload.isbn.or(existing.isbn),
    };

    conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![updated.title, updated.author, updated.year, updated.isbn, updated.id],
    )
    .unwrap();

    (StatusCode::OK, Json(serde_json::to_value(&updated).unwrap()))
}

async fn delete_book(
    State(db): State<Db>,
    Path(id): Path<String>,
) -> (StatusCode, Json<serde_json::Value>) {
    let conn = db.lock().unwrap();
    let rows = conn
        .execute("DELETE FROM books WHERE id = ?1", params![id])
        .unwrap();
    if rows == 0 {
        (
            StatusCode::NOT_FOUND,
            Json(serde_json::json!({ "error": "book not found" })),
        )
    } else {
        (StatusCode::OK, Json(serde_json::json!({ "deleted": true })))
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

fn row_to_book(row: &rusqlite::Row<'_>) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

// ── App builder (shared with tests) ──────────────────────────────────────────

pub fn build_app(db: Db) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book).get(list_books))
        .route("/books/:id", get(get_book).put(update_book).delete(delete_book))
        .with_state(db)
}

// ── Entry point ───────────────────────────────────────────────────────────────

#[tokio::main]
async fn main() {
    let conn = Connection::open("books.db").expect("failed to open database");
    init_db(&conn);
    let db: Db = Arc::new(Mutex::new(conn));

    let app = build_app(db);

    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000")
        .await
        .expect("failed to bind");
    println!("Listening on http://0.0.0.0:3000");
    axum::serve(listener, app).await.expect("server error");
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::http::{Method, Request};
    use http_body_util::BodyExt;
    use tower::ServiceExt;

    fn test_app() -> Router {
        let conn = Connection::open_in_memory().expect("in-memory db");
        init_db(&conn);
        let db: Db = Arc::new(Mutex::new(conn));
        build_app(db)
    }

    async fn body_json(body: Body) -> serde_json::Value {
        let bytes = body.collect().await.unwrap().to_bytes();
        serde_json::from_slice(&bytes).unwrap()
    }

    #[tokio::test]
    async fn test_health_check() {
        let app = test_app();
        let resp = app
            .oneshot(
                Request::builder()
                    .uri("/health")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(resp.status(), StatusCode::OK);
        let json = body_json(resp.into_body()).await;
        assert_eq!(json["status"], "ok");
    }

    #[tokio::test]
    async fn test_create_and_get_book() {
        let app = test_app();

        // Create a book
        let create_resp = app
            .clone()
            .oneshot(
                Request::builder()
                    .method(Method::POST)
                    .uri("/books")
                    .header("content-type", "application/json")
                    .body(Body::from(
                        r#"{"title":"Rust Programming","author":"Steve Klabnik","year":2019}"#,
                    ))
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(create_resp.status(), StatusCode::CREATED);
        let created = body_json(create_resp.into_body()).await;
        let id = created["id"].as_str().unwrap().to_string();
        assert_eq!(created["title"], "Rust Programming");
        assert_eq!(created["author"], "Steve Klabnik");

        // Fetch the book by ID
        let get_resp = app
            .oneshot(
                Request::builder()
                    .uri(format!("/books/{}", id))
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(get_resp.status(), StatusCode::OK);
        let fetched = body_json(get_resp.into_body()).await;
        assert_eq!(fetched["id"], id);
        assert_eq!(fetched["title"], "Rust Programming");
    }

    #[tokio::test]
    async fn test_create_book_missing_required_fields() {
        let app = test_app();

        // Missing author
        let resp = app
            .clone()
            .oneshot(
                Request::builder()
                    .method(Method::POST)
                    .uri("/books")
                    .header("content-type", "application/json")
                    .body(Body::from(r#"{"title":"Only Title"}"#))
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(resp.status(), StatusCode::UNPROCESSABLE_ENTITY);
        let json = body_json(resp.into_body()).await;
        assert!(json["error"].as_str().unwrap().contains("author"));

        // Missing title
        let resp2 = app
            .oneshot(
                Request::builder()
                    .method(Method::POST)
                    .uri("/books")
                    .header("content-type", "application/json")
                    .body(Body::from(r#"{"author":"Only Author"}"#))
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(resp2.status(), StatusCode::UNPROCESSABLE_ENTITY);
        let json2 = body_json(resp2.into_body()).await;
        assert!(json2["error"].as_str().unwrap().contains("title"));
    }

    #[tokio::test]
    async fn test_list_books_with_author_filter() {
        let app = test_app();

        // Create two books by different authors
        for body in &[
            r#"{"title":"Book A","author":"Alice"}"#,
            r#"{"title":"Book B","author":"Bob"}"#,
            r#"{"title":"Book C","author":"Alice"}"#,
        ] {
            app.clone()
                .oneshot(
                    Request::builder()
                        .method(Method::POST)
                        .uri("/books")
                        .header("content-type", "application/json")
                        .body(Body::from(*body))
                        .unwrap(),
                )
                .await
                .unwrap();
        }

        // Filter by author Alice
        let resp = app
            .oneshot(
                Request::builder()
                    .uri("/books?author=Alice")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(resp.status(), StatusCode::OK);
        let books = body_json(resp.into_body()).await;
        let arr = books.as_array().unwrap();
        assert_eq!(arr.len(), 2);
        assert!(arr.iter().all(|b| b["author"] == "Alice"));
    }

    #[tokio::test]
    async fn test_update_book() {
        let app = test_app();

        let create_resp = app
            .clone()
            .oneshot(
                Request::builder()
                    .method(Method::POST)
                    .uri("/books")
                    .header("content-type", "application/json")
                    .body(Body::from(r#"{"title":"Old Title","author":"Author"}"#))
                    .unwrap(),
            )
            .await
            .unwrap();
        let created = body_json(create_resp.into_body()).await;
        let id = created["id"].as_str().unwrap().to_string();

        let update_resp = app
            .clone()
            .oneshot(
                Request::builder()
                    .method(Method::PUT)
                    .uri(format!("/books/{}", id))
                    .header("content-type", "application/json")
                    .body(Body::from(r#"{"title":"New Title"}"#))
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(update_resp.status(), StatusCode::OK);
        let updated = body_json(update_resp.into_body()).await;
        assert_eq!(updated["title"], "New Title");
        assert_eq!(updated["author"], "Author"); // unchanged
    }

    #[tokio::test]
    async fn test_delete_book() {
        let app = test_app();

        let create_resp = app
            .clone()
            .oneshot(
                Request::builder()
                    .method(Method::POST)
                    .uri("/books")
                    .header("content-type", "application/json")
                    .body(Body::from(r#"{"title":"To Delete","author":"Author"}"#))
                    .unwrap(),
            )
            .await
            .unwrap();
        let created = body_json(create_resp.into_body()).await;
        let id = created["id"].as_str().unwrap().to_string();

        // Delete it
        let del_resp = app
            .clone()
            .oneshot(
                Request::builder()
                    .method(Method::DELETE)
                    .uri(format!("/books/{}", id))
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(del_resp.status(), StatusCode::OK);

        // Fetching should return 404
        let get_resp = app
            .oneshot(
                Request::builder()
                    .uri(format!("/books/{}", id))
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(get_resp.status(), StatusCode::NOT_FOUND);
    }

    #[tokio::test]
    async fn test_get_nonexistent_book() {
        let app = test_app();
        let resp = app
            .oneshot(
                Request::builder()
                    .uri("/books/nonexistent-id")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::NOT_FOUND);
    }
}
