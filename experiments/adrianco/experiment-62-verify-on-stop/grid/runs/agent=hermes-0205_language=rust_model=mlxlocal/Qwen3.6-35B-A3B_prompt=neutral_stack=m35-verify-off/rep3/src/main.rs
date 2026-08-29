use actix_web::{web, App, HttpServer, HttpResponse, Responder};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use thiserror::Error;
use uuid::Uuid;

// ─── Models ───────────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Book {
    pub id: String,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct CreateBookRequest {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct UpdateBookRequest {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct FilterParams {
    pub author: Option<String>,
}

// ─── Error types ──────────────────────────────────────────────────────────────

#[derive(Error, Debug)]
pub enum AppError {
    #[error("Validation failed: {0}")]
    Validation(String),
    #[error("Book not found")]
    NotFound,
    #[error("Database error: {0}")]
    Database(#[from] rusqlite::Error),
}

impl actix_web::ResponseError for AppError {
    fn status_code(&self) -> actix_web::http::StatusCode {
        match self {
            AppError::Validation(_) => actix_web::http::StatusCode::BAD_REQUEST,
            AppError::NotFound => actix_web::http::StatusCode::NOT_FOUND,
            AppError::Database(_) => actix_web::http::StatusCode::INTERNAL_SERVER_ERROR,
        }
    }
}

// ─── Database helpers ─────────────────────────────────────────────────────────

fn create_table(conn: &Connection) -> rusqlite::Result<()> {
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        );",
    )?;
    Ok(())
}

fn book_from_row(row: &rusqlite::Row) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3).unwrap_or(None),
        isbn: row.get(4).unwrap_or(None),
    })
}

// ─── Handlers ─────────────────────────────────────────────────────────────────

pub async fn health_check() -> impl Responder {
    HttpResponse::Ok().json(serde_json::json!({"status": "healthy"}))
}

pub async fn create_book(
    payload: web::Json<CreateBookRequest>,
    db: web::Data<std::sync::Arc<std::sync::Mutex<Connection>>>,
) -> Result<HttpResponse, AppError> {
    let mut errors = Vec::new();
    let title = match &payload.title {
        Some(t) if !t.trim().is_empty() => t.trim().to_string(),
        _ => {
            errors.push("title is required".to_string());
            String::new()
        }
    };
    let author = match &payload.author {
        Some(a) if !a.trim().is_empty() => a.trim().to_string(),
        _ => {
            errors.push("author is required".to_string());
            String::new()
        }
    };

    if !errors.is_empty() {
        return Err(AppError::Validation(errors.join(", ")));
    }

    let id = Uuid::new_v4().to_string();
    let year = payload.year;
    let isbn = payload.isbn.clone();

    let conn = db.lock().map_err(|e| AppError::Validation(e.to_string()))?;
    conn.execute(
        "INSERT INTO books (id, title, author, year, isbn) VALUES (?1, ?2, ?3, ?4, ?5)",
        params![&id, &title, &author, year, isbn],
    )?;

    let book = Book {
        id,
        title,
        author,
        year,
        isbn,
    };

    Ok(HttpResponse::Created().json(book))
}

pub async fn list_books(
    query: web::Query<FilterParams>,
    db: web::Data<std::sync::Arc<std::sync::Mutex<Connection>>>,
) -> Result<HttpResponse, AppError> {
    let conn = db.lock().map_err(|e| AppError::Validation(e.to_string()))?;

    let books: Vec<Book> = if let Some(author) = &query.author {
        let mut stmt = conn.prepare(
            "SELECT id, title, author, year, isbn FROM books WHERE author = ?1",
        )?;
        let mut rows = stmt.query(params![author])?;
        let mut results = Vec::new();
        while let Some(row) = rows.next()? {
            results.push(book_from_row(row)?);
        }
        results
    } else {
        let mut stmt = conn.prepare("SELECT id, title, author, year, isbn FROM books")?;
        let mut rows = stmt.query([])?;
        let mut results = Vec::new();
        while let Some(row) = rows.next()? {
            results.push(book_from_row(row)?);
        }
        results
    };

    Ok(HttpResponse::Ok().json(books))
}

pub async fn get_book(
    path: web::Path<String>,
    db: web::Data<std::sync::Arc<std::sync::Mutex<Connection>>>,
) -> Result<HttpResponse, AppError> {
    let id = path.into_inner();
    let conn = db.lock().map_err(|e| AppError::Validation(e.to_string()))?;

    let book: Book = conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        params![&id],
        book_from_row,
    )?;

    Ok(HttpResponse::Ok().json(book))
}

pub async fn update_book(
    path: web::Path<String>,
    payload: web::Json<UpdateBookRequest>,
    db: web::Data<std::sync::Arc<std::sync::Mutex<Connection>>>,
) -> Result<HttpResponse, AppError> {
    let inner = &payload.0;
    if inner.title.is_none()
        && inner.author.is_none()
        && inner.year.is_none()
        && inner.isbn.is_none()
    {
        return Err(AppError::Validation(
            "At least one field must be provided".to_string(),
        ));
    }

    let id = path.into_inner();
    let conn = db.lock().map_err(|e| AppError::Validation(e.to_string()))?;

    let existing: Book = conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        params![&id],
        book_from_row,
    )?;

    let new_title = inner.title.as_ref().cloned().unwrap_or_else(|| existing.title.clone());
    let new_author = inner.author.as_ref().cloned().unwrap_or_else(|| existing.author.clone());
    let new_year = inner.year.or(existing.year);
    let new_isbn = inner.isbn.as_ref().cloned().or(existing.isbn);

    conn.execute(
        "UPDATE books SET title = ?2, author = ?3, year = ?4, isbn = ?5 WHERE id = ?1",
        params![&id, &new_title, &new_author, new_year, new_isbn],
    )?;

    let book = Book {
        id,
        title: new_title,
        author: new_author,
        year: new_year,
        isbn: new_isbn,
    };

    Ok(HttpResponse::Ok().json(book))
}

pub async fn delete_book(
    path: web::Path<String>,
    db: web::Data<std::sync::Arc<std::sync::Mutex<Connection>>>,
) -> Result<HttpResponse, AppError> {
    let id = path.into_inner();
    let conn = db.lock().map_err(|e| AppError::Validation(e.to_string()))?;

    let exists: Result<Book, _> = conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        params![&id],
        book_from_row,
    );

    if exists.is_err() {
        return Err(AppError::NotFound);
    }

    conn.execute("DELETE FROM books WHERE id = ?1", params![&id])?;

    Ok(HttpResponse::NoContent().finish())
}

// ─── Helpers for tests and main ───────────────────────────────────────────────

pub fn init_db(db_path: &str) -> std::sync::Arc<std::sync::Mutex<Connection>> {
    let conn = Connection::open(db_path).expect("Failed to open database");
    create_table(&conn).expect("Failed to create table");
    std::sync::Arc::new(std::sync::Mutex::new(conn))
}

pub fn make_app_factory(
    db: std::sync::Arc<std::sync::Mutex<Connection>>,
) -> impl Fn() -> actix_web::dev::AppService + Clone {
    move || {
        let app = App::new()
            .app_data(web::Data::new(db.clone()))
            .route("/health", web::get().to(health_check))
            .route("/books", web::post().to(create_book))
            .route("/books", web::get().to(list_books))
            .route("/books/{id}", web::get().to(get_book))
            .route("/books/{id}", web::put().to(update_book))
            .route("/books/{id}", web::delete().to(delete_book));
        app.into_service()
    }
}

// ─── Main ─────────────────────────────────────────────────────────────────────

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let db = init_db("books.db");

    println!("Book API server running on http://localhost:8080");

    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(db.clone()))
            .route("/health", web::get().to(health_check))
            .route("/books", web::post().to(create_book))
            .route("/books", web::get().to(list_books))
            .route("/books/{id}", web::get().to(get_book))
            .route("/books/{id}", web::put().to(update_book))
            .route("/books/{id}", web::delete().to(delete_book))
    })
    .bind("0.0.0.0:8080")?
    .run()
    .await
}
