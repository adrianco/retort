use crate::db;
use crate::models::{Book, BookFilter, CreateBook, UpdateBook};
use crate::DbPool;
use actix_web::{web, HttpResponse};
use serde_json::json;
use uuid::Uuid;

pub async fn health_check() -> HttpResponse {
    HttpResponse::Ok().json(json!({"status": "ok"}))
}

pub async fn create_book(
    pool: web::Data<DbPool>,
    body: web::Json<CreateBook>,
) -> HttpResponse {
    let title = match &body.title {
        Some(t) if !t.trim().is_empty() => t.trim().to_string(),
        _ => {
            return HttpResponse::BadRequest()
                .json(json!({"error": "title is required"}));
        }
    };
    let author = match &body.author {
        Some(a) if !a.trim().is_empty() => a.trim().to_string(),
        _ => {
            return HttpResponse::BadRequest()
                .json(json!({"error": "author is required"}));
        }
    };

    let book = Book {
        id: Uuid::new_v4().to_string(),
        title,
        author,
        year: body.year,
        isbn: body.isbn.clone(),
    };

    match db::insert_book(&pool, &book) {
        Ok(_) => HttpResponse::Created().json(&book),
        Err(e) => HttpResponse::InternalServerError()
            .json(json!({"error": e.to_string()})),
    }
}

pub async fn list_books(
    pool: web::Data<DbPool>,
    query: web::Query<BookFilter>,
) -> HttpResponse {
    let author_filter = query.author.as_deref();
    match db::get_all_books(&pool, author_filter) {
        Ok(books) => HttpResponse::Ok().json(books),
        Err(e) => HttpResponse::InternalServerError()
            .json(json!({"error": e.to_string()})),
    }
}

pub async fn get_book(
    pool: web::Data<DbPool>,
    path: web::Path<String>,
) -> HttpResponse {
    let id = path.into_inner();
    match db::get_book_by_id(&pool, &id) {
        Ok(Some(book)) => HttpResponse::Ok().json(book),
        Ok(None) => HttpResponse::NotFound().json(json!({"error": "book not found"})),
        Err(e) => HttpResponse::InternalServerError()
            .json(json!({"error": e.to_string()})),
    }
}

pub async fn update_book(
    pool: web::Data<DbPool>,
    path: web::Path<String>,
    body: web::Json<UpdateBook>,
) -> HttpResponse {
    let id = path.into_inner();

    let existing = match db::get_book_by_id(&pool, &id) {
        Ok(Some(b)) => b,
        Ok(None) => {
            return HttpResponse::NotFound().json(json!({"error": "book not found"}));
        }
        Err(e) => {
            return HttpResponse::InternalServerError()
                .json(json!({"error": e.to_string()}));
        }
    };

    let title = match &body.title {
        Some(t) if !t.trim().is_empty() => t.trim().to_string(),
        Some(_) => {
            return HttpResponse::BadRequest()
                .json(json!({"error": "title cannot be empty"}));
        }
        None => existing.title.clone(),
    };
    let author = match &body.author {
        Some(a) if !a.trim().is_empty() => a.trim().to_string(),
        Some(_) => {
            return HttpResponse::BadRequest()
                .json(json!({"error": "author cannot be empty"}));
        }
        None => existing.author.clone(),
    };

    let updated = Book {
        id: existing.id,
        title,
        author,
        year: body.year.or(existing.year),
        isbn: body.isbn.clone().or(existing.isbn),
    };

    match db::update_book_in_db(&pool, &updated) {
        Ok(_) => HttpResponse::Ok().json(&updated),
        Err(e) => HttpResponse::InternalServerError()
            .json(json!({"error": e.to_string()})),
    }
}

pub async fn delete_book(
    pool: web::Data<DbPool>,
    path: web::Path<String>,
) -> HttpResponse {
    let id = path.into_inner();
    match db::delete_book_from_db(&pool, &id) {
        Ok(0) => HttpResponse::NotFound().json(json!({"error": "book not found"})),
        Ok(_) => HttpResponse::NoContent().finish(),
        Err(e) => HttpResponse::InternalServerError()
            .json(json!({"error": e.to_string()})),
    }
}
