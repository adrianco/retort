use actix_web::{web, HttpResponse};

use crate::models::{self, CreateBookRequest, UpdateBookRequest};

use serde::Deserialize;

#[derive(Deserialize)]
pub struct QueryParams {
    pub author: Option<String>,
}

#[derive(serde::Serialize)]
pub struct HealthResponse {
    pub status: String,
}

pub async fn health() -> HttpResponse {
    HttpResponse::Ok().json(HealthResponse {
        status: "ok".to_string(),
    })
}

pub async fn list_books(
    pool: web::Data<sqlx::Pool<sqlx::Sqlite>>,
    query: web::Query<QueryParams>,
) -> HttpResponse {
    match models::get_books(pool.get_ref(), query.author.clone()).await {
        Ok(books) => HttpResponse::Ok().json(books),
        Err(e) => HttpResponse::InternalServerError().json(serde_json::json!({
            "error": e.to_string()
        })),
    }
}

pub async fn create_book(
    pool: web::Data<sqlx::Pool<sqlx::Sqlite>>,
    body: web::Json<CreateBookRequest>,
) -> HttpResponse {
    match models::create_book(pool.get_ref(), body.into_inner()).await {
        Ok(book) => HttpResponse::Created().json(book),
        Err(e) => HttpResponse::BadRequest().json(serde_json::json!({
            "error": e.to_string()
        })),
    }
}

pub async fn get_book_by_id(
    pool: web::Data<sqlx::Pool<sqlx::Sqlite>>,
    path: web::Path<i64>,
) -> HttpResponse {
    let id = path.into_inner();
    match models::get_book(pool.get_ref(), id).await {
        Ok(book) => HttpResponse::Ok().json(book),
        Err(e) => HttpResponse::NotFound().json(serde_json::json!({
            "error": e.to_string()
        })),
    }
}

pub async fn update_book(
    pool: web::Data<sqlx::Pool<sqlx::Sqlite>>,
    path: web::Path<i64>,
    body: web::Json<UpdateBookRequest>,
) -> HttpResponse {
    let id = path.into_inner();
    match models::update_book(pool.get_ref(), id, body.into_inner()).await {
        Ok(book) => HttpResponse::Ok().json(book),
        Err(e) => HttpResponse::NotFound().json(serde_json::json!({
            "error": e.to_string()
        })),
    }
}

pub async fn delete_book(
    pool: web::Data<sqlx::Pool<sqlx::Sqlite>>,
    path: web::Path<i64>,
) -> HttpResponse {
    let id = path.into_inner();
    match models::delete_book(pool.get_ref(), id).await {
        Ok(()) => HttpResponse::NoContent().finish(),
        Err(e) => HttpResponse::NotFound().json(serde_json::json!({
            "error": e.to_string()
        })),
    }
}

pub fn configure(cfg: &mut web::ServiceConfig) {
    cfg.service(
        web::scope("/books")
            .route("", web::get().to(list_books))
            .route("", web::post().to(create_book))
            .route("/{id}", web::get().to(get_book_by_id))
            .route("/{id}", web::put().to(update_book))
            .route("/{id}", web::delete().to(delete_book)),
    )
    .route("/health", web::get().to(health));
}
