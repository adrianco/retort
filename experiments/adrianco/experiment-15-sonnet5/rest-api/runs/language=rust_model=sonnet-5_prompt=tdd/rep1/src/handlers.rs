use crate::db;
use crate::models::BookInput;
use crate::SharedConn;
use axum::extract::{Path, Query, State};
use axum::http::StatusCode;
use axum::Json;
use serde::Deserialize;
use serde_json::{json, Value};

#[derive(Debug, Deserialize)]
pub struct ListBooksQuery {
    pub author: Option<String>,
}

pub async fn health() -> Json<Value> {
    Json(json!({ "status": "ok" }))
}

pub async fn create_book(
    State(conn): State<SharedConn>,
    Json(input): Json<BookInput>,
) -> Result<(StatusCode, Json<Value>), (StatusCode, Json<Value>)> {
    if let Err(message) = input.validate() {
        return Err((StatusCode::BAD_REQUEST, Json(json!({ "error": message }))));
    }

    let conn = conn.lock().unwrap();
    let book = db::insert_book(&conn, &input)
        .map_err(|e| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({ "error": e.to_string() })),
            )
        })?;

    Ok((StatusCode::CREATED, Json(serde_json::to_value(book).unwrap())))
}

pub async fn list_books(
    State(conn): State<SharedConn>,
    Query(query): Query<ListBooksQuery>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let conn = conn.lock().unwrap();
    let books = db::list_books(&conn, query.author.as_deref()).map_err(|e| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({ "error": e.to_string() })),
        )
    })?;

    Ok(Json(serde_json::to_value(books).unwrap()))
}

pub async fn get_book(
    State(conn): State<SharedConn>,
    Path(id): Path<i64>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let conn = conn.lock().unwrap();
    let book = db::get_book(&conn, id).map_err(|e| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({ "error": e.to_string() })),
        )
    })?;

    match book {
        Some(book) => Ok(Json(serde_json::to_value(book).unwrap())),
        None => Err((
            StatusCode::NOT_FOUND,
            Json(json!({ "error": "book not found" })),
        )),
    }
}

pub async fn update_book(
    State(conn): State<SharedConn>,
    Path(id): Path<i64>,
    Json(input): Json<BookInput>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    if let Err(message) = input.validate() {
        return Err((StatusCode::BAD_REQUEST, Json(json!({ "error": message }))));
    }

    let conn = conn.lock().unwrap();
    let book = db::update_book(&conn, id, &input).map_err(|e| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({ "error": e.to_string() })),
        )
    })?;

    match book {
        Some(book) => Ok(Json(serde_json::to_value(book).unwrap())),
        None => Err((
            StatusCode::NOT_FOUND,
            Json(json!({ "error": "book not found" })),
        )),
    }
}

pub async fn delete_book(
    State(conn): State<SharedConn>,
    Path(id): Path<i64>,
) -> Result<StatusCode, (StatusCode, Json<Value>)> {
    let conn = conn.lock().unwrap();
    let deleted = db::delete_book(&conn, id).map_err(|e| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({ "error": e.to_string() })),
        )
    })?;

    if deleted {
        Ok(StatusCode::NO_CONTENT)
    } else {
        Err((
            StatusCode::NOT_FOUND,
            Json(json!({ "error": "book not found" })),
        ))
    }
}
