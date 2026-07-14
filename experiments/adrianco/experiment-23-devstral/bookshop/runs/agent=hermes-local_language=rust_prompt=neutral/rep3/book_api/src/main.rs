#[macro_use]
extern crate diesel;

use actix_web::{web, App, HttpServer, HttpResponse, Responder, Error};
use diesel::prelude::*;
use diesel::sqlite::SqliteConnection;
use dotenv::dotenv;
use serde::Deserialize;
use uuid::Uuid;

mod models;
mod schema;
use models::Book;

#[derive(Deserialize)]
struct BookFilter {
    author: Option<String>,
}

async fn create_book(
    db: web::Data<SqliteConnection>, 
    item: web::Json<Book>
) -> Result<HttpResponse, Error> {
    let new_book = Book {
        id: Uuid::new_v4(),
        ..item.into_inner()
    };
    
    web::block(move || {
        diesel::insert_into(schema::books::table)
            .values(&new_book)
            .execute(&*db)
    }).await.map_err(|_| actix_web::error::ErrorInternalServerError("Error creating book"))?;
    
    Ok(HttpResponse::Created().json(new_book))
}

async fn get_books(
    db: web::Data<SqliteConnection>, 
    query: web::Query<BookFilter>
) -> Result<HttpResponse, Error> {
    let results = web::block(move || {
        let mut query = schema::books::table.into_boxed::<SqliteConnection>();
        if let Some(author) = &query.author {
            query = query.filter(schema::books::author.eq(author));
        }
        query.load::<Book>(&*db)
    }).await.map_err(|_| actix_web::error::ErrorInternalServerError("Error loading books"))?;
    
    Ok(HttpResponse::Ok().json(results))
}

async fn get_book(
    db: web::Data<SqliteConnection>, 
    book_id: web::Path<Uuid>
) -> Result<HttpResponse, Error> {
    let result = web::block(move || {
        schema::books::table.find(book_id.into_inner())
            .get_result::<Book>(&*db)
    }).await.map_err(|_| actix_web::error::ErrorInternalServerError("Error loading book"))?;
    
    Ok(HttpResponse::Ok().json(result))
}

async fn update_book(
    db: web::Data<SqliteConnection>, 
    book_id: web::Path<Uuid>, 
    item: web::Json<Book>
) -> Result<HttpResponse, Error> {
    let book = item.into_inner();
    
    web::block(move || {
        diesel::update(schema::books::table.find(book_id.into_inner()))
            .set(&book)
            .execute(&*db)
    }).await.map_err(|_| actix_web::error::ErrorInternalServerError("Error updating book"))?;
    
    Ok(HttpResponse::Ok().json(book))
}

async fn delete_book(
    db: web::Data<SqliteConnection>, 
    book_id: web::Path<Uuid>
) -> Result<HttpResponse, Error> {
    web::block(move || {
        diesel::delete(schema::books::table.find(book_id.into_inner()))
            .execute(&*db)
    }).await.map_err(|_| actix_web::error::ErrorInternalServerError("Error deleting book"))?;
    
    Ok(HttpResponse::NoContent().finish())
}

async fn health_check() -> impl Responder {
    HttpResponse::Ok().body("OK")
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    dotenv().ok();
    
    let database_url = std::env::var("DATABASE_URL")
        .expect("DATABASE_URL must be set");
    let connection = SqliteConnection::establish(&database_url)
        .expect(&format!("Error connecting to {}", database_url));

    std::env::set_var("RUST_LOG", "actix_web=info");
    env_logger::init();

    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(connection.clone()))
            .route("/health", web::get().to(health_check))
            .service(
                web::scope("/books")
                    .route("", web::post().to(create_book))
                    .route("", web::get().to(get_books))
                    .route("/{id}", web::get().to(get_book))
                    .route("/{id}", web::put().to(update_book))
                    .route("/{id}", web::delete().to(delete_book))
            )
    }).bind("127.0.0.1:8080")?
    .run()
    .await
}
