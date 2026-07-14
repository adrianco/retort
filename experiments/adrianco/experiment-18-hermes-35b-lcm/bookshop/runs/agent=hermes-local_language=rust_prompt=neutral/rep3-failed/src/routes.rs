use actix_web::{web, HttpResponse, Responder};
use std::collections::HashMap;

use crate::db::Database;
use crate::models::{CreateBookRequest, UpdateBookRequest};

pub async fn create_book(
    db: web::Data<Database>,
    body: web::Json<CreateBookRequest>,
) -> impl Responder {
    if body.title.as_ref().map_or(true, |t| t.trim().is_empty())
        || body.author.as_ref().map_or(true, |a| a.trim().is_empty())
    {
        return HttpResponse::BadRequest()
            .json(serde_json::json!({
                "error": "Title and author are required"
            }));
    }

    match db.create_book(&body) {
        Ok(book) => HttpResponse::Created().json(book),
        Err(e) => HttpResponse::InternalServerError().json(serde_json::json!({
            "error": e.to_string()
        })),
    }
}

pub async fn list_books(
    db: web::Data<Database>,
    query: web::Query<HashMap<String, String>>,
) -> impl Responder {
    let author = query.get("author").map(|s| s.as_str());

    match db.list_books(author) {
        Ok(books) => HttpResponse::Ok().json(books),
        Err(e) => HttpResponse::InternalServerError().json(serde_json::json!({
            "error": e.to_string()
        })),
    }
}

pub async fn get_book(
    db: web::Data<Database>,
    path: web::Path<String>,
) -> impl Responder {
    let id = path.into_inner();
    match db.get_book(&id) {
        Ok(Some(book)) => HttpResponse::Ok().json(book),
        Ok(None) => HttpResponse::NotFound().json(serde_json::json!({
            "error": "Book not found"
        })),
        Err(e) => HttpResponse::InternalServerError().json(serde_json::json!({
            "error": e.to_string()
        })),
    }
}

pub async fn update_book(
    db: web::Data<Database>,
    path: web::Path<String>,
    body: web::Json<UpdateBookRequest>,
) -> impl Responder {
    let id = path.into_inner();
    match db.update_book(&id, &body) {
        Ok(Some(book)) => HttpResponse::Ok().json(book),
        Ok(None) => HttpResponse::NotFound().json(serde_json::json!({
            "error": "Book not found"
        })),
        Err(e) => HttpResponse::InternalServerError().json(serde_json::json!({
            "error": e.to_string()
        })),
    }
}

pub async fn delete_book(
    db: web::Data<Database>,
    path: web::Path<String>,
) -> impl Responder {
    let id = path.into_inner();
    match db.delete_book(&id) {
        Ok(true) => HttpResponse::NoContent().finish(),
        Ok(false) => HttpResponse::NotFound().json(serde_json::json!({
            "error": "Book not found"
        })),
        Err(e) => HttpResponse::InternalServerError().json(serde_json::json!({
            "error": e.to_string()
        })),
    }
}

pub async fn health_check() -> impl Responder {
    HttpResponse::Ok().json(serde_json::json!({
        "status": "healthy"
    }))
}
