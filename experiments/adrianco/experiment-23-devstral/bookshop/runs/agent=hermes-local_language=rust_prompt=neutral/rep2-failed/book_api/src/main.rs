#[macro_use]
extern crate diesel;

mod db;
mod models;
mod schema;

use actix_web::{web, App, HttpResponse, HttpServer, Responder};
use diesel::prelude::*;
use diesel::sqlite::SqliteConnection;
use serde_json::json;
use uuid::Uuid;
use validator::Validate;

use crate::db::{establish_connection, run_migrations};
use crate::models::{Book, NewBook, UpdateBook};
use crate::schema::books::dsl::*;

async fn create_book(
    db: web::Data<SqliteConnection>,
    item: web::Json<NewBook<'_>>,
) -> impl Responder {
    if let Err(err) = item.validate() {
        return HttpResponse::BadRequest().json(json!({"error": err.to_string()}));
    }

    let new_book = NewBook::new(
        item.title.as_ref(),
        item.author.as_ref(),
        item.year,
        item.isbn.as_deref(),
    );

    diesel::insert_into(books)
        .values(&new_book)
        .execute(&mut **db)
        .expect("Error saving new book");

    HttpResponse::Created().json(item.into_inner())
}

async fn list_books(
    db: web::Data<SqliteConnection>,
    author: web::Query<Option<String>>,
) -> impl Responder {
    let author_filter = author.into_inner();
    let result = if let Some(ref author_filter) = author_filter {
        books.filter(author.eq(author_filter)).load::<Book>(&mut **db)
    } else {
        books.load::<Book>(&mut **db)
    };

    match result {
        Ok(items) => HttpResponse::Ok().json(items),
        Err(_) => HttpResponse::InternalServerError().json(json!({"error": "Error loading books"})),
    }
}

async fn get_book(
    db: web::Data<SqliteConnection>,
    book_id: web::Path<Uuid>,
) -> impl Responder {
    let result = books.filter(id.eq(book_id.into_inner())).first::<Book>(&mut **db);

    match result {
        Ok(book) => HttpResponse::Ok().json(book),
        Err(_) => HttpResponse::NotFound().json(json!({"error": "Book not found"})),
    }
}

async fn update_book(
    db: web::Data<SqliteConnection>,
    book_id: web::Path<Uuid>,
    item: web::Json<UpdateBook<'_>>,
) -> impl Responder {
    if let Err(err) = item.validate() {
        return HttpResponse::BadRequest().json(json!({"error": err.to_string()}));
    }

    let result = diesel::update(books.find(book_id.into_inner()))
        .set(&*item)
        .execute(&mut **db);

    match result {
        Ok(_) => HttpResponse::Ok().finish(),
        Err(_) => HttpResponse::NotFound().json(json!({"error": "Book not found"})),
    }
}

async fn delete_book(
    db: web::Data<SqliteConnection>,
    book_id: web::Path<Uuid>,
) -> impl Responder {
    let result = diesel::delete(books.find(book_id.into_inner())).execute(&mut **db);

    match result {
        Ok(_) => HttpResponse::Ok().finish(),
        Err(_) => HttpResponse::NotFound().json(json!({"error": "Book not found"})),
    }
}

async fn health_check() -> impl Responder {
    HttpResponse::Ok().json(json!({"status": "healthy"}))
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let connection = establish_connection();
    run_migrations(&connection);
    let connection = web::Data::new(connection);

    HttpServer::new(move || {
        App::new()
            .app_data(connection.clone())
            .route("/books", web::post().to(create_book))
            .route("/books", web::get().to(list_books))
            .route("/books/{id}", web::get().to(get_book))
            .route("/books/{id}", web::put().to(update_book))
            .route("/books/{id}", web::delete().to(delete_book))
            .route("/health", web::get().to(health_check))
    })
    .bind("127.0.0.1:8080")?
    .run()
    .await
}
