use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use sqlx::{sqlite::SqlitePoolOptions, SqlitePool};
use std::{env, net::SocketAddr};

#[derive(Clone)]
struct AppState {
    db: SqlitePool,
}

#[derive(Debug, Serialize, Deserialize, sqlx::FromRow)]
struct Book {
    id: i64,
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
struct BookInput {
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Deserialize)]
struct ListQuery {
    author: Option<String>,
}

#[derive(Serialize)]
struct ErrorBody {
    error: &'static str,
}

struct ApiError(StatusCode, &'static str);

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        (self.0, Json(ErrorBody { error: self.1 })).into_response()
    }
}

fn validate(input: &BookInput) -> Result<(), ApiError> {
    if input.title.trim().is_empty() || input.author.trim().is_empty() {
        return Err(ApiError(
            StatusCode::BAD_REQUEST,
            "title and author are required",
        ));
    }
    Ok(())
}

async fn create_book(
    State(state): State<AppState>,
    Json(input): Json<BookInput>,
) -> Result<impl IntoResponse, ApiError> {
    validate(&input)?;
    let result = sqlx::query("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)")
        .bind(input.title.trim())
        .bind(input.author.trim())
        .bind(input.year)
        .bind(input.isbn)
        .execute(&state.db)
        .await
        .map_err(|_| ApiError(StatusCode::INTERNAL_SERVER_ERROR, "database error"))?;
    let book = get_book_row(&state.db, result.last_insert_rowid()).await?;
    Ok((StatusCode::CREATED, Json(book)))
}

async fn list_books(
    State(state): State<AppState>,
    Query(query): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let books = if let Some(author) = query.author {
        sqlx::query_as::<_, Book>(
            "SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id",
        )
        .bind(author)
        .fetch_all(&state.db)
        .await
    } else {
        sqlx::query_as::<_, Book>("SELECT id, title, author, year, isbn FROM books ORDER BY id")
            .fetch_all(&state.db)
            .await
    }
    .map_err(|_| ApiError(StatusCode::INTERNAL_SERVER_ERROR, "database error"))?;
    Ok(Json(books))
}

async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, ApiError> {
    Ok(Json(get_book_row(&state.db, id).await?))
}

async fn get_book_row(db: &SqlitePool, id: i64) -> Result<Book, ApiError> {
    sqlx::query_as::<_, Book>("SELECT id, title, author, year, isbn FROM books WHERE id = ?")
        .bind(id)
        .fetch_optional(db)
        .await
        .map_err(|_| ApiError(StatusCode::INTERNAL_SERVER_ERROR, "database error"))?
        .ok_or(ApiError(StatusCode::NOT_FOUND, "book not found"))
}

async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Json(input): Json<BookInput>,
) -> Result<Json<Book>, ApiError> {
    validate(&input)?;
    let result =
        sqlx::query("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?")
            .bind(input.title.trim())
            .bind(input.author.trim())
            .bind(input.year)
            .bind(input.isbn)
            .bind(id)
            .execute(&state.db)
            .await
            .map_err(|_| ApiError(StatusCode::INTERNAL_SERVER_ERROR, "database error"))?;
    if result.rows_affected() == 0 {
        return Err(ApiError(StatusCode::NOT_FOUND, "book not found"));
    }
    Ok(Json(get_book_row(&state.db, id).await?))
}

async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<StatusCode, ApiError> {
    let result = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(id)
        .execute(&state.db)
        .await
        .map_err(|_| ApiError(StatusCode::INTERNAL_SERVER_ERROR, "database error"))?;
    if result.rows_affected() == 0 {
        return Err(ApiError(StatusCode::NOT_FOUND, "book not found"));
    }
    Ok(StatusCode::NO_CONTENT)
}

async fn health() -> &'static str {
    "ok"
}

fn app(db: SqlitePool) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book).get(list_books))
        .route(
            "/books/:id",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(AppState { db })
}

async fn database(url: &str) -> Result<SqlitePool, sqlx::Error> {
    let db = SqlitePoolOptions::new()
        .max_connections(5)
        .connect(url)
        .await?;
    sqlx::query(
        "CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )",
    )
    .execute(&db)
    .await?;
    Ok(db)
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let url = env::var("DATABASE_URL").unwrap_or_else(|_| "sqlite://books.db".to_string());
    let db = database(&url).await?;
    let addr: SocketAddr = env::var("BIND_ADDR")
        .unwrap_or_else(|_| "127.0.0.1:3000".to_string())
        .parse()?;
    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app(db)).await?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{body::Body, http::Request};
    use http_body_util::BodyExt;
    use serde_json::{json, Value};
    use tower::ServiceExt;

    async fn test_app() -> Router {
        let db = SqlitePoolOptions::new()
            .max_connections(1)
            .connect("sqlite::memory:")
            .await
            .unwrap();
        sqlx::query("CREATE TABLE books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)")
            .execute(&db).await.unwrap();
        app(db)
    }

    async fn request(
        app: Router,
        method: &str,
        uri: &str,
        body: Option<Value>,
    ) -> (StatusCode, Value) {
        let mut builder = Request::builder().method(method).uri(uri);
        if body.is_some() {
            builder = builder.header("content-type", "application/json");
        }
        let req = builder
            .body(Body::from(body.map(|v| v.to_string()).unwrap_or_default()))
            .unwrap();
        let response = app.oneshot(req).await.unwrap();
        let status = response.status();
        let bytes = response.into_body().collect().await.unwrap().to_bytes();
        let value = if bytes.is_empty() {
            Value::Null
        } else {
            serde_json::from_slice(&bytes).unwrap()
        };
        (status, value)
    }

    #[tokio::test]
    async fn health_returns_ok() {
        let (status, body) = request(test_app().await, "GET", "/health", None).await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(body, json!("ok"));
    }

    #[tokio::test]
    async fn create_and_retrieve_book() {
        let app = test_app().await;
        let (status, book) = request(
            app.clone(),
            "POST",
            "/books",
            Some(
                json!({"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}),
            ),
        )
        .await;
        assert_eq!(status, StatusCode::CREATED);
        assert_eq!(book["id"], 1);
        assert_eq!(book["title"], "Dune");
        let (status, found) = request(app, "GET", "/books/1", None).await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(found["author"], "Frank Herbert");
    }

    #[tokio::test]
    async fn rejects_missing_required_fields_and_unknown_ids() {
        let app = test_app().await;
        let (status, _) = request(
            app.clone(),
            "POST",
            "/books",
            Some(json!({"title":" ","author":"A"})),
        )
        .await;
        assert_eq!(status, StatusCode::BAD_REQUEST);
        let (status, _) = request(app, "GET", "/books/99", None).await;
        assert_eq!(status, StatusCode::NOT_FOUND);
    }

    #[tokio::test]
    async fn filters_lists_and_supports_update_and_delete() {
        let app = test_app().await;
        request(
            app.clone(),
            "POST",
            "/books",
            Some(json!({"title":"Dune","author":"Frank Herbert"})),
        )
        .await;
        request(
            app.clone(),
            "POST",
            "/books",
            Some(json!({"title":"Foundation","author":"Isaac Asimov"})),
        )
        .await;
        let (status, books) =
            request(app.clone(), "GET", "/books?author=Isaac%20Asimov", None).await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(books.as_array().unwrap().len(), 1);
        assert_eq!(books[0]["title"], "Foundation");
        let (status, updated) = request(
            app.clone(),
            "PUT",
            "/books/1",
            Some(json!({"title":"Dune Messiah","author":"Frank Herbert"})),
        )
        .await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(updated["title"], "Dune Messiah");
        let (status, _) = request(app.clone(), "DELETE", "/books/1", None).await;
        assert_eq!(status, StatusCode::NO_CONTENT);
        let (status, _) = request(app, "GET", "/books/1", None).await;
        assert_eq!(status, StatusCode::NOT_FOUND);
    }
}
