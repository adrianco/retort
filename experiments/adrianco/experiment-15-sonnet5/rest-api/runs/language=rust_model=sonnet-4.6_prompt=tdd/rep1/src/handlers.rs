use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::Json,
};
use rusqlite::Connection;
use serde_json::{json, Value};
use std::sync::{Arc, Mutex};

use crate::db;
use crate::models::{BookFilter, CreateBook, UpdateBook};

pub type AppState = Arc<Mutex<Connection>>;

pub async fn health() -> Json<Value> {
    Json(json!({"status": "ok"}))
}

pub async fn create_book(
    State(state): State<AppState>,
    Json(input): Json<CreateBook>,
) -> (StatusCode, Json<Value>) {
    if input.title.as_deref().map(|s| s.trim()).unwrap_or("").is_empty() {
        return (
            StatusCode::UNPROCESSABLE_ENTITY,
            Json(json!({"error": "title is required"})),
        );
    }
    if input.author.as_deref().map(|s| s.trim()).unwrap_or("").is_empty() {
        return (
            StatusCode::UNPROCESSABLE_ENTITY,
            Json(json!({"error": "author is required"})),
        );
    }

    let conn = state.lock().unwrap();
    match db::create_book(&conn, &input) {
        Ok(book) => (StatusCode::CREATED, Json(json!(book))),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({"error": e.to_string()})),
        ),
    }
}

pub async fn list_books(
    State(state): State<AppState>,
    Query(filter): Query<BookFilter>,
) -> (StatusCode, Json<Value>) {
    let conn = state.lock().unwrap();
    match db::list_books(&conn, filter.author.as_deref()) {
        Ok(books) => (StatusCode::OK, Json(json!(books))),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({"error": e.to_string()})),
        ),
    }
}

pub async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> (StatusCode, Json<Value>) {
    let conn = state.lock().unwrap();
    match db::get_book(&conn, &id) {
        Ok(Some(book)) => (StatusCode::OK, Json(json!(book))),
        Ok(None) => (StatusCode::NOT_FOUND, Json(json!({"error": "book not found"}))),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({"error": e.to_string()})),
        ),
    }
}

pub async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<String>,
    Json(input): Json<UpdateBook>,
) -> (StatusCode, Json<Value>) {
    let conn = state.lock().unwrap();
    match db::update_book(&conn, &id, &input) {
        Ok(Some(book)) => (StatusCode::OK, Json(json!(book))),
        Ok(None) => (StatusCode::NOT_FOUND, Json(json!({"error": "book not found"}))),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({"error": e.to_string()})),
        ),
    }
}

pub async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> (StatusCode, Json<Value>) {
    let conn = state.lock().unwrap();
    match db::delete_book(&conn, &id) {
        Ok(true) => (StatusCode::OK, Json(json!({"deleted": true}))),
        Ok(false) => (StatusCode::NOT_FOUND, Json(json!({"error": "book not found"}))),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({"error": e.to_string()})),
        ),
    }
}
