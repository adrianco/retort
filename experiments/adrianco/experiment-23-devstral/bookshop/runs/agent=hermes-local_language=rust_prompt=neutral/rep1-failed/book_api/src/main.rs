use actix_web::{web, App, HttpServer, HttpResponse, Responder, Error};
use serde::{Deserialize, Serialize};
use serde_json::json;
use sqlx::sqlite::SqlitePoolOptions;
use sqlx::SqlitePool;
use sqlx::FromRow;
use sqlx::Row;
use uuid::Uuid;
use validator::{Validate, ValidationErrors};
use validator::ValidationError;
use std::fmt;

#[derive(Serialize, Deserialize, Clone)]
struct Book {
    id: Option<Uuid>,
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

impl Validate for Book {
    fn validate(&self) -> Result<(), ValidationErrors> {
        let mut errors = ValidationErrors::new();
        if self.title.is_empty() {
            errors.add("title", ValidationError::new("title").message("Title is required"));
        }
        if self.author.is_empty() {
            errors.add("author", ValidationError::new("author").message("Author is required"));
        }
        if errors.is_empty() {
            Ok(())
        } else {
            Err(errors)
        }
    }
}

impl FromRow<'_> for Book {
    fn from_row(row: &sqlx::sqlite::SqliteRow) -> Result<Self, sqlx::Error> {
        Ok(Self {
            id: row.get("id"),
            title: row.get("title"),
            author: row.get("author"),
            year: row.get("year"),
            isbn: row.get("isbn"),
        })
    }
}

#[derive(Debug, Clone)]
struct MyError {
    message: String,
}

impl fmt::Display for MyError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.message)
    }
}

impl std::error::Error for MyError {}

impl From<sqlx::Error> for MyError {
    fn from(err: sqlx::Error) -> Self {
        MyError {
            message: err.to_string(),
        }
    }
}

impl actix_web::ResponseError for MyError {
    fn error_response(&self) -> HttpResponse {
        HttpResponse::BadRequest().json(self.message.clone())
    }
}

async fn create_book(
    pool: web::Data<SqlitePool>,
    book: web::Json<Book>
) -> Result<impl Responder, Error> {
    if let Err(errors) = book.validate() {
        return Ok(HttpResponse::BadRequest().json(errors.to_string()));
    }

    let query = "INSERT INTO books (id, title, author, year, isbn) VALUES (?1, ?2, ?3, ?4, ?5)";
    sqlx::query(query)
        .bind(book.id.unwrap_or_else(Uuid::new_v4).to_string())
        .bind(&book.title)
        .bind(&book.author)
        .bind(&book.year)
        .bind(&book.isbn)
        .execute(&**pool)
        .await.map_err(MyError::from)?;

    Ok(HttpResponse::Created().json(book))
}

async fn get_books(
    pool: web::Data<SqlitePool>,
    author: web::Query<Option<String>>
) -> Result<impl Responder, Error> {
    let mut query = String::from("SELECT * FROM books");
    let mut rows = Vec::new();
    if let Some(author_filter) = author.into_inner() {
        query.push_str(" WHERE author LIKE ?");
        rows = sqlx::query_as::<_, Book>(&query)
            .bind(format!("%{}%", author_filter))
            .fetch_all(&**pool)
            .await.map_err(MyError::from)?;
    } else {
        rows = sqlx::query_as::<_, Book>(&query)
            .fetch_all(&**pool)
            .await.map_err(MyError::from)?;
    }
    Ok(HttpResponse::Ok().json(rows))
}

async fn get_book(
    pool: web::Data<SqlitePool>,
    book_id: web::Path<Uuid>
) -> Result<impl Responder, Error> {
    let row = sqlx::query_as::<_, Book>("SELECT * FROM books WHERE id = ?")
        .bind(book_id.into_inner().to_string())
        .fetch_one(&**pool)
        .await.map_err(MyError::from)?;
    Ok(HttpResponse::Ok().json(row))
}

async fn update_book(
    pool: web::Data<SqlitePool>,
    book_id: web::Path<Uuid>,
    book: web::Json<Book>
) -> Result<impl Responder, Error> {
    if let Err(errors) = book.validate() {
        return Ok(HttpResponse::BadRequest().json(errors.to_string()));
    }

    let query = "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5";
    sqlx::query(query)
        .bind(&book.title)
        .bind(&book.author)
        .bind(&book.year)
        .bind(&book.isbn)
        .bind(book_id.into_inner().to_string())
        .execute(&**pool)
        .await.map_err(MyError::from)?;

    Ok(HttpResponse::Ok().json(book))
}

async fn delete_book(
    pool: web::Data<SqlitePool>,
    book_id: web::Path<Uuid>
) -> Result<impl Responder, Error> {
    sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(book_id.into_inner().to_string())
        .execute(&**pool)
        .await.map_err(MyError::from)?;

    Ok(HttpResponse::Ok().json(json!({"result": "Book deleted"})))
}

async fn health_check() -> impl Responder {
    HttpResponse::Ok().json(json!({"status": "healthy"}))
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Initialize database
    let pool = SqlitePoolOptions::new()
        .max_connections(5)
        .connect("sqlite:books.db")
        .await
        .expect("Failed to create pool.");

    // Create tables
    sqlx::query(
        "CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )"
    )
    .execute(&pool)
    .await
    .expect("Failed to create table");

    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(pool.clone()))
            .route("/health", web::get().to(health_check))
            .route("/books", web::post().to(create_book))
            .route("/books", web::get().to(get_books))
            .route("/books/{id}", web::get().to(get_book))
            .route("/books/{id}", web::put().to(update_book))
            .route("/books/{id}", web::delete().to(delete_book))
    })
    .bind("127.0.0.1:8080")?
    .run()
    .await
}
