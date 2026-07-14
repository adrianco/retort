use actix_web::{web, HttpResponse, Responder};
use diesel::prelude::*;
use diesel::sqlite::SqliteConnection;
use dotenvy::dotenv;
use serde_json::json;
use std::env;

use crate::models::{Book, NewBook};
use crate::schema::books::dsl::*;

pub fn establish_connection() -> SqliteConnection {
    dotenv().ok();
    let database_url = env::var("DATABASE_URL").unwrap_or_else(|_| "test.sqlite".to_string());
    let connection = SqliteConnection::establish(&database_url)
        .unwrap_or_else(|_| panic!("Error connecting to database"));

    // Run migrations
    diesel::sql_query("CREATE TABLE IF NOT EXISTS books (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT
    )").execute(&connection).unwrap();

    connection
}

pub fn create_book(
    db: web::Data<SqliteConnection>,
    item: web::Json<NewBook>,
) -> impl Responder {
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

pub fn list_books(
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

pub fn get_book(
    db: web::Data<SqliteConnection>,
    book_id: web::Path<Uuid>,
) -> impl Responder {
    let result = books.filter(id.eq(book_id.into_inner())).first::<Book>(&mut **db);

    match result {
        Ok(book) => HttpResponse::Ok().json(book),
        Err(_) => HttpResponse::NotFound().json(json!({"error": "Book not found"})),
    }
}

pub fn delete_book(
    db: web::Data<SqliteConnection>,
    book_id: web::Path<Uuid>,
) -> impl Responder {
    let result = diesel::delete(books.find(book_id.into_inner())).execute(&mut **db);

    match result {
        Ok(_) => HttpResponse::Ok().finish(),
        Err(_) => HttpResponse::NotFound().json(json!({"error": "Book not found"})),
    }
}
