use actix_web::{web, App, HttpServer, HttpResponse, Result};
use serde::{Deserialize, Serialize};
use sqlite::Connection;
use std::sync::Mutex;

#[derive(Serialize, Deserialize)]
struct Book {
    id: Option<i64>,
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Serialize, Deserialize)]
struct BookCreate {
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Serialize, Deserialize)]
struct BookUpdate {
    title: Option<String>,
    author: Option<String>,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Serialize, Deserialize)]
struct HealthResponse {
    status: String,
}

#[web::get("/health")]
async fn health_check() -> HttpResponse {
    HttpResponse::Ok().json(HealthResponse { status: "OK".into() })
}

#[web::get("/books")]
async fn get_books(db: web::Data<Mutex<Connection>>) -> HttpResponse {
    let db = db.lock().unwrap();
    let mut statement = db.prepare("SELECT id, title, author, year, isbn FROM books").unwrap();
    let mut rows = statement.query([]).unwrap();
    
    let mut books = Vec::new();
    while let Some(row) = rows.next() {
        let row = row.unwrap();
        let book = Book {
            id: Some(row.column(0).unwrap()),
            title: row.column(1).unwrap(),
            author: row.column(2).unwrap(),
            year: Some(row.column(3).unwrap()),
            isbn: Some(row.get(4).unwrap_or(String::new())),
        };
        books.push(book);
    }
    
    HttpResponse::Ok().json(books)
}

#[web::get("/books/{id}")]
async fn get_book(path: web::Path<i64>, db: web::Data<Mutex<Connection>>) -> HttpResponse {
    let db = db.lock().unwrap();
    let mut stmt = db.prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?").unwrap();
    let mut rows = stmt.query([path.into_inner]).unwrap();
    
    match rows.next() {
        Some(row) => {
            let row = row.unwrap();
            let book = Book {
                id: Some(row.column(0).unwrap()),
                title: row.column(1).unwrap(),
                author: row.column(2).unwrap(),
                year: Some(row.column(3).unwrap()),
                isbn: Some(row.get(4).unwrap_or(String::new())),
            };
            HttpResponse::Ok().json(book)
        },
        None => HttpResponse::NotFound().json("Book not found"),
    }
}

#[web::post("/books")]
async fn create_book(book: web::Json<BookCreate>, db: web::Data<Mutex<Connection>>) -> HttpResponse {
    let db = db.lock().unwrap();
    let mut stmt = db.prepare("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)").unwrap();
    
    let result = stmt.execute([
        book.title.as_str(),
        book.author.as_str(),
        book.year.map(|y| y.to_string()).unwrap_or(String::new()).as_str(),
        book.isbn.as_ref().unwrap_or(&String::new()).as_str(),
    ]);
    
    match result {
        Ok(_) => {
            let last_insert_rowid = db.last_insert_rowid();
            let mut stmt = db.prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?").unwrap();
            let mut rows = stmt.query([last_insert_rowid]).unwrap();
            
            match rows.next() {
                Some(row) => {
                    let row = row.unwrap();
                    let book = Book {
                        id: Some(row.column(0).unwrap()),
                        title: row.column(1).unwrap(),
                        author: row.column(2).unwrap(),
                        year: Some(row.column(3).unwrap()),
                        isbn: Some(row.get(4).unwrap_or(String::new)),
                    };
                    HttpResponse::Created().json(book)
                }
                None => HttpResponse::InternalServerError().json("Failed to create book"),
            }
        }
        Err(e) => HttpResponse::InternalServerError().json(format!("Error: {:?}", e)),
    }
}

#[web::put("/books/{id}")]
async fn update_book(path: web::Path<i64>, book: web::Json<BookUpdate>, db: web::Data<Mutex<Connection>>) -> HttpResponse {
    let db = db.lock().unwrap();
    let mut stmt = db.prepare("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?").unwrap();
    
    let result = stmt.execute([
        book.title.as_ref().unwrap_or(&String::new()).as_str(),
        book.author.as_ref().unwrap_or(&String::new()).as_str(),
        book.year.map(|y| y.to_string()).unwrap_or(String::new()).as_str(),
        book.isbn.as_ref().unwrap_or(&String::new()).as_str(),
        path.into_inner().to_string().as_str(),
    ]);
    
    match result {
        Ok(_) => {
            let mut stmt = db.prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?").unwrap();
            let mut rows = stmt.query([path.into_inner]).unwrap();
            
            match rows.next() {
                Some(row) => {
                    let row = row.unwrap();
                    let book = Book {
                        id: Some(row.column(0).unwrap()),
                        title: row.column(1).unwrap(),
                        author: row.column(2).unwrap(),
                        year: Some(row.column(3).unwrap()),
                        isbn: Some(row.get(4).unwrap_or(String::new)),
                    };
                    HttpResponse::Ok().json(book)
                }
                None => HttpResponse::NotFound().json("Book not found"),
            }
        }
        Err(e) => HttpResponse::InternalServerError().json(format!("Error: {:?}", e)),
    }
}

#[web::delete("/books/{id}")]
async fn delete_book(path: web::Path<i64>, db: web::Data<Mutex<Connection>>) -> HttpResponse {
    let db = db.lock().unwrap();
    let mut stmt = db.prepare("DELETE FROM books WHERE id = ?").unwrap();
    
    let result = stmt.execute([path.into_inner]);
    
    match result {
        Ok(_) => HttpResponse::Ok().json("Book deleted"),
        Err(e) => HttpResponse::InternalServerError().json(format!("Error: {:?}", e)),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Create database connection
    let db = Mutex::new(sqlite::open("books.db").unwrap());
    
    // Initialize database schema
    {
        let db = db.lock().unwrap();
        db.execute("CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )").unwrap();
    }
    
    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(db.clone()))
            .service(health_check)
            .service(get_books)
            .service(get_book)
            .service(create_book)
 .service(delete_book)
 .service(update_book)
    })
    .bind("127.0.0.1:8080")
    .unwrap()
    .run()
 .await
}