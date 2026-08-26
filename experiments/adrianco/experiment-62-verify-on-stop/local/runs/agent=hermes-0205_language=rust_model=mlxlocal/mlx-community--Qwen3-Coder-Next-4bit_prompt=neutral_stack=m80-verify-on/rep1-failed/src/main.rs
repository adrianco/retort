// edition: 2021
use axum::{
    extract::Path,
    http::StatusCode,
    response::Json,
    routing::{delete, get, post, put},
    Router,
};
use std::sync::Arc;
use tokio::sync::Mutex;

use crate::{
    database::{create_book, delete_book, get_all_books, get_book_by_id, update_book},
    models::{AppError, Book, BookInput, BookUpdate},
};

mod database;
mod models;

async fn health() -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "ok",
    }))
}

async fn list_books(
    state: axum::extract::State<Arc<Mutex<crate::database::DbPool>>>,
    author: Option<String>,
) -> Result<Json<Vec<Book>>, AppError> {
    let pool = state.lock().await;
    let books = get_all_books(&pool, author).await?;
    Ok(Json(books))
}

async fn get_book(
    state: axum::extract::State<Arc<Mutex<crate::database::DbPool>>>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, AppError> {
    let pool = state.lock().await;
    let book = get_book_by_id(&pool, id).await?;
    Ok(Json(book))
}

async fn create_book_handler(
    state: axum::extract::State<Arc<Mutex<crate::database::DbPool>>>,
    Json(input): Json<BookInput>,
) -> Result<(StatusCode, Json<Book>), AppError> {
    let pool = state.lock().await;
    let book = create_book(&pool, input).await?;
    Ok((StatusCode::CREATED, Json(book)))
}

async fn update_book_handler(
    state: axum::extract::State<Arc<Mutex<crate::database::DbPool>>>,
    Path(id): Path<i64>,
    Json(update): Json<BookUpdate>,
) -> Result<Json<Book>, AppError> {
    let pool = state.lock().await;
    let book = update_book(&pool, id, update).await?;
    Ok(Json(book))
}

async fn delete_book_handler(
    state: axum::extract::State<Arc<Mutex<crate::database::DbPool>>>,
    Path(id): Path<i64>,
) -> Result<StatusCode, AppError> {
    let pool = state.lock().await;
    delete_book(&pool, id).await?;
    Ok(StatusCode::NO_CONTENT)
}

#[tokio::main]
async fn main() {
    let pool = crate::database::init_db("books.db")
        .await
        .expect("Failed to initialize database");

    let state = Arc::new(Mutex::new(pool));
    let app = Router::new()
        .with_state(state.clone())
        .route("/health", get(health))
        .route("/books", post(create_book_handler).get(list_books))
        .route("/books/{id}", put(update_book_handler).delete(delete_book_handler))
        .route("/books/{id}", get(get_book));

    let listener = tokio::net::TcpListener::bind("127.0.0.1:3000")
        .await
        .unwrap();
    println!("Server running on http://127.0.0.1:3000");
    axum::serve(listener, app);
}
