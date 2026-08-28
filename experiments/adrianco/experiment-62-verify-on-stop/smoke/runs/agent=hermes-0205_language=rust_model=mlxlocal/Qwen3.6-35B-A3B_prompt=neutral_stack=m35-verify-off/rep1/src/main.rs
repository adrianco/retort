use actix_web::{web, App, HttpServer, HttpResponse, get, post, put, delete};
use serde::{Deserialize, Serialize};
use rusqlite::{Connection, Result as SqliteResult, params, OptionalExtension};
use std::sync::{Arc, Mutex};

// --- Models ---

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Book {
    pub id: i64,
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

// --- Database ---

#[derive(Clone)]
pub struct Db {
    pub conn: Arc<Mutex<Connection>>,
}

impl Db {
    pub fn init() -> SqliteResult<Self> {
        let conn = Arc::new(Mutex::new(Connection::open_in_memory()?));
        {
            let db = conn.lock().unwrap();
            db.execute_batch(
                "CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year INTEGER,
                    isbn TEXT
                );",
            )?;
        }
        Ok(Db { conn })
    }

    pub fn create_book(&self, title: &str, author: &str, year: Option<i32>, isbn: Option<&str>) -> SqliteResult<Book> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare(
            "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        )?;
        let id = stmt.insert(params![title, author, year, isbn])?;
        Ok(Book { id, title: title.to_string(), author: author.to_string(), year, isbn: isbn.map(|s| s.to_string()) })
    }

    pub fn list_books(&self, author_filter: Option<&str>) -> SqliteResult<Vec<Book>> {
        let conn = self.conn.lock().unwrap();
        let books = match author_filter {
            Some(author) => {
                let mut stmt = conn.prepare("SELECT id, title, author, year, isbn FROM books WHERE author = ?1")?;
                let mut rows = stmt.query(params![author])?;
                collect_books(&mut rows)
            }
            None => {
                let mut stmt = conn.prepare("SELECT id, title, author, year, isbn FROM books")?;
                let mut rows = stmt.query([])?;
                collect_books(&mut rows)
            }
        };
        books
    }

    pub fn get_book(&self, id: i64) -> SqliteResult<Option<Book>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?1")?;
        stmt.query_row(params![id], |row| {
            Ok(Book {
                id: row.get(0)?,
                title: row.get(1)?,
                author: row.get(2)?,
                year: row.get(3)?,
                isbn: row.get(4)?,
            })
        }).optional()
    }

    pub fn update_book(&self, id: i64, title: Option<&str>, author: Option<&str>, year: Option<i32>, isbn: Option<&str>) -> SqliteResult<Option<Book>> {
        let conn = self.conn.lock().unwrap();
        // Fetch current book using raw query
        let book = conn.query_row("SELECT id, title, author, year, isbn FROM books WHERE id = ?1", params![id], |row| {
            Ok(Book {
                id: row.get(0)?,
                title: row.get(1)?,
                author: row.get(2)?,
                year: row.get(3)?,
                isbn: row.get(4)?,
            })
        }).optional()?;

        let book = match book {
            Some(b) => b,
            None => return Ok(None),
        };

        let new_title = title.unwrap_or(&book.title);
        let new_author = author.unwrap_or(&book.author);
        let new_year = year.or(book.year);
        let new_isbn = isbn.or(book.isbn.as_deref());

        conn.execute(
            "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
            params![new_title, new_author, new_year, new_isbn, id],
        )?;

        Ok(Some(Book {
            id,
            title: new_title.to_string(),
            author: new_author.to_string(),
            year: new_year,
            isbn: new_isbn.map(|s| s.to_string()),
        }))
    }

    pub fn delete_book(&self, id: i64) -> SqliteResult<bool> {
        let conn = self.conn.lock().unwrap();
        let changes = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
        Ok(changes > 0)
    }
}

fn collect_books(rows: &mut rusqlite::Rows) -> SqliteResult<Vec<Book>> {
    let mut books = Vec::new();
    while let Some(row) = rows.next()? {
        books.push(Book {
            id: row.get(0)?,
            title: row.get(1)?,
            author: row.get(2)?,
            year: row.get(3)?,
            isbn: row.get(4)?,
        });
    }
    Ok(books)
}

// --- Handlers ---

#[get("/health")]
async fn health_check() -> HttpResponse {
    HttpResponse::Ok().json(serde_json::json!({ "status": "ok" }))
}

#[post("/books")]
async fn create_book(body: web::Json<CreateBookRequest>, db: web::Data<Db>) -> HttpResponse {
    let req = body.into_inner();
    // Validate: title and author are required
    let title = match req.title {
        Some(t) if !t.trim().is_empty() => t,
        _ => return HttpResponse::BadRequest().json(serde_json::json!({ "error": "title is required" })),
    };
    let author = match req.author {
        Some(a) if !a.trim().is_empty() => a,
        _ => return HttpResponse::BadRequest().json(serde_json::json!({ "error": "author is required" })),
    };

    match db.create_book(&title, &author, req.year, req.isbn.as_deref()) {
        Ok(book) => HttpResponse::Created().json(book),
        Err(_) => HttpResponse::InternalServerError().json(serde_json::json!({ "error": "failed to create book" })),
    }
}

#[get("/books")]
async fn list_books(query: web::Query<std::collections::HashMap<String, String>>, db: web::Data<Db>) -> HttpResponse {
    let author_filter = query.get("author").map(|s| s.as_str());
    match db.list_books(author_filter) {
        Ok(books) => HttpResponse::Ok().json(books),
        Err(_) => HttpResponse::InternalServerError().json(serde_json::json!({ "error": "failed to list books" })),
    }
}

#[get("/books/{id}")]
async fn get_book(path: web::Path<i64>, db: web::Data<Db>) -> HttpResponse {
    match db.get_book(path.into_inner()) {
        Ok(Some(book)) => HttpResponse::Ok().json(book),
        Ok(None) => HttpResponse::NotFound().json(serde_json::json!({ "error": "book not found" })),
        Err(_) => HttpResponse::InternalServerError().json(serde_json::json!({ "error": "failed to get book" })),
    }
}

#[put("/books/{id}")]
async fn update_book(path: web::Path<i64>, body: web::Json<UpdateBookRequest>, db: web::Data<Db>) -> HttpResponse {
    let req = body.into_inner();
    let id = path.into_inner();

    // For update, validate title and author if provided
    if let Some(ref title) = req.title {
        if title.trim().is_empty() {
            return HttpResponse::BadRequest().json(serde_json::json!({ "error": "title cannot be empty" }));
        }
    }
    if let Some(ref author) = req.author {
        if author.trim().is_empty() {
            return HttpResponse::BadRequest().json(serde_json::json!({ "error": "author cannot be empty" }));
        }
    }

    match db.update_book(id, req.title.as_deref(), req.author.as_deref(), req.year, req.isbn.as_deref()) {
        Ok(Some(book)) => HttpResponse::Ok().json(book),
        Ok(None) => HttpResponse::NotFound().json(serde_json::json!({ "error": "book not found" })),
        Err(_) => HttpResponse::InternalServerError().json(serde_json::json!({ "error": "failed to update book" })),
    }
}

#[delete("/books/{id}")]
async fn delete_book(path: web::Path<i64>, db: web::Data<Db>) -> HttpResponse {
    let id = path.into_inner();
    match db.delete_book(id) {
        Ok(true) => HttpResponse::NoContent().finish(),
        Ok(false) => HttpResponse::NotFound().json(serde_json::json!({ "error": "book not found" })),
        Err(_) => HttpResponse::InternalServerError().json(serde_json::json!({ "error": "failed to delete book" })),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let db = Db::init().expect("Failed to initialize database");
    println!("Starting book API server on http://0.0.0.0:8080");

    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(db.clone()))
            .service(health_check)
            .service(create_book)
            .service(list_books)
            .service(get_book)
            .service(update_book)
            .service(delete_book)
    })
    .bind("0.0.0.0:8080")?
    .run()
    .await
}

// --- Tests ---

#[cfg(test)]
mod tests {
    use super::*;
    use actix_web::{test, App, web};
    use serde_json::json;

    fn get_test_db() -> Db {
        Db::init().expect("Failed to init test db")
    }

    #[actix_web::test]
    async fn test_health_check() {
        let db = get_test_db();
        let app = test::init_service(
            App::new()
                .app_data(web::Data::new(db))
                .service(health_check),
        )
        .await;

        let req = test::TestRequest::get().uri("/health").to_request();
        let resp = test::call_service(&app, req).await;
        assert!(resp.status().is_success());

        let body: serde_json::Value = serde_json::from_slice(
            &actix_web::test::read_body(resp).await
        ).unwrap();
        assert_eq!(body["status"], "ok");
    }

    #[actix_web::test]
    async fn test_create_book() {
        let db = get_test_db();
        let app = test::init_service(
            App::new()
                .app_data(web::Data::new(db))
                .service(create_book),
        )
        .await;

        let req = test::TestRequest::post()
            .uri("/books")
            .set_json(json!({
                "title": "The Great Gatsby",
                "author": "F. Scott Fitzgerald",
                "year": 1925,
                "isbn": "978-0743273565"
            }))
            .to_request();

        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), 201);

        let body: Book = serde_json::from_slice(
            &actix_web::test::read_body(resp).await
        ).unwrap();
        assert_eq!(body.title, "The Great Gatsby");
        assert_eq!(body.author, "F. Scott Fitzgerald");
        assert_eq!(body.year, Some(1925));
    }

    #[actix_web::test]
    async fn test_create_book_missing_title() {
        let db = get_test_db();
        let app = test::init_service(
            App::new()
                .app_data(web::Data::new(db))
                .service(create_book),
        )
        .await;

        let req = test::TestRequest::post()
            .uri("/books")
            .set_json(json!({
                "author": "Some Author"
            }))
            .to_request();

        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), 400);

        let body: serde_json::Value = serde_json::from_slice(
            &actix_web::test::read_body(resp).await
        ).unwrap();
        assert_eq!(body["error"], "title is required");
    }

    #[actix_web::test]
    async fn test_create_book_missing_author() {
        let db = get_test_db();
        let app = test::init_service(
            App::new()
                .app_data(web::Data::new(db))
                .service(create_book),
        )
        .await;

        let req = test::TestRequest::post()
            .uri("/books")
            .set_json(json!({
                "title": "Some Book"
            }))
            .to_request();

        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), 400);

        let body: serde_json::Value = serde_json::from_slice(
            &actix_web::test::read_body(resp).await
        ).unwrap();
        assert_eq!(body["error"], "author is required");
    }

    #[actix_web::test]
    async fn test_list_books() {
        let db = get_test_db();
        // Insert test data
        db.create_book("The Great Gatsby", "F. Scott Fitzgerald", Some(1925), Some("978-0743273565")).unwrap();
        db.create_book("To Kill a Mockingbird", "Harper Lee", Some(1960), Some("978-0061120084")).unwrap();
        db.create_book("The Catcher in the Rye", "J.D. Salinger", Some(1951), Some("978-0316769488")).unwrap();

        let app = test::init_service(
            App::new()
                .app_data(web::Data::new(db))
                .service(list_books),
        )
        .await;

        let req = test::TestRequest::get().uri("/books").to_request();
        let resp = test::call_service(&app, req).await;
        assert!(resp.status().is_success());

        let body: Vec<Book> = serde_json::from_slice(
            &actix_web::test::read_body(resp).await
        ).unwrap();
        assert_eq!(body.len(), 3);
    }

    #[actix_web::test]
    async fn test_list_books_filter_by_author() {
        let db = get_test_db();
        db.create_book("The Great Gatsby", "F. Scott Fitzgerald", Some(1925), Some("978-0743273565")).unwrap();
        db.create_book("To Kill a Mockingbird", "Harper Lee", Some(1960), Some("978-0061120084")).unwrap();
        db.create_book("The Catcher in the Rye", "J.D. Salinger", Some(1951), Some("978-0316769488")).unwrap();

        let app = test::init_service(
            App::new()
                .app_data(web::Data::new(db))
                .service(list_books),
        )
        .await;

        let req = test::TestRequest::get()
            .uri("/books?author=F.%20Scott%20Fitzgerald")
            .to_request();

        let resp = test::call_service(&app, req).await;
        assert!(resp.status().is_success());

        let body: Vec<Book> = serde_json::from_slice(
            &actix_web::test::read_body(resp).await
        ).unwrap();
        assert_eq!(body.len(), 1);
        assert_eq!(body[0].title, "The Great Gatsby");
    }

    #[actix_web::test]
    async fn test_get_book() {
        let db = get_test_db();
        let book = db.create_book("The Great Gatsby", "F. Scott Fitzgerald", Some(1925), Some("978-0743273565")).unwrap();

        let app = test::init_service(
            App::new()
                .app_data(web::Data::new(db))
                .service(get_book),
        )
        .await;

        let req = test::TestRequest::get().uri(&format!("/books/{}", book.id)).to_request();
        let resp = test::call_service(&app, req).await;
        assert!(resp.status().is_success());

        let body: Book = serde_json::from_slice(
            &actix_web::test::read_body(resp).await
        ).unwrap();
        assert_eq!(body.id, book.id);
        assert_eq!(body.title, "The Great Gatsby");
    }

    #[actix_web::test]
    async fn test_get_book_not_found() {
        let db = get_test_db();
        let app = test::init_service(
            App::new()
                .app_data(web::Data::new(db))
                .service(get_book),
        )
        .await;

        let req = test::TestRequest::get().uri("/books/999").to_request();
        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), 404);
    }

    #[actix_web::test]
    async fn test_update_book() {
        let db = get_test_db();
        let book = db.create_book("The Great Gatsby", "F. Scott Fitzgerald", Some(1925), Some("978-0743273565")).unwrap();

        let app = test::init_service(
            App::new()
                .app_data(web::Data::new(db))
                .service(update_book),
        )
        .await;

        let req = test::TestRequest::put()
            .uri(&format!("/books/{}", book.id))
            .set_json(json!({
                "title": "The Great Gatsby (Updated)"
            }))
            .to_request();

        let resp = test::call_service(&app, req).await;
        assert!(resp.status().is_success());

        let body: Book = serde_json::from_slice(
            &actix_web::test::read_body(resp).await
        ).unwrap();
        assert_eq!(body.title, "The Great Gatsby (Updated)");
        assert_eq!(body.author, "F. Scott Fitzgerald");
    }

    #[actix_web::test]
    async fn test_update_book_not_found() {
        let db = get_test_db();
        let app = test::init_service(
            App::new()
                .app_data(web::Data::new(db))
                .service(update_book),
        )
        .await;

        let req = test::TestRequest::put()
            .uri("/books/999")
            .set_json(json!({
                "title": "Some Title"
            }))
            .to_request();

        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), 404);
    }

    #[actix_web::test]
    async fn test_delete_book() {
        let db = get_test_db();
        let book = db.create_book("The Great Gatsby", "F. Scott Fitzgerald", Some(1925), Some("978-0743273565")).unwrap();

        let app = test::init_service(
            App::new()
                .app_data(web::Data::new(db))
                .service(delete_book),
        )
        .await;

        let req = test::TestRequest::delete()
            .uri(&format!("/books/{}", book.id))
            .to_request();

        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), 204);

        // Verify it's gone
        let req2 = test::TestRequest::get().uri(&format!("/books/{}", book.id)).to_request();
        let resp2 = test::call_service(&app, req2).await;
        assert_eq!(resp2.status(), 404);
    }

    #[actix_web::test]
    async fn test_delete_book_not_found() {
        let db = get_test_db();
        let app = test::init_service(
            App::new()
                .app_data(web::Data::new(db))
                .service(delete_book),
        )
        .await;

        let req = test::TestRequest::delete().uri("/books/999").to_request();
        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), 404);
    }

    #[actix_web::test]
    async fn test_full_crud_workflow() {
        let db = get_test_db();
        let app = test::init_service(
            App::new()
                .app_data(web::Data::new(db.clone()))
                .service(create_book)
                .service(list_books)
                .service(get_book)
                .service(update_book)
                .service(delete_book)
                .service(health_check),
        )
        .await;

        // Create
        let req = test::TestRequest::post()
            .uri("/books")
            .set_json(json!({
                "title": "1984",
                "author": "George Orwell",
                "year": 1949,
                "isbn": "978-0451524935"
            }))
            .to_request();
        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), 201);
        let body: Book = serde_json::from_slice(
            &actix_web::test::read_body(resp).await
        ).unwrap();
        let book_id = body.id;

        // Read
        let req = test::TestRequest::get().uri(&format!("/books/{}", book_id)).to_request();
        let resp = test::call_service(&app, req).await;
        assert!(resp.status().is_success());

        // Update
        let req = test::TestRequest::put()
            .uri(&format!("/books/{}", book_id))
            .set_json(json!({
                "title": "1984 (Special Edition)"
            }))
            .to_request();
        let resp = test::call_service(&app, req).await;
        assert!(resp.status().is_success());

        // List
        let req = test::TestRequest::get().uri("/books").to_request();
        let resp = test::call_service(&app, req).await;
        assert!(resp.status().is_success());
        let body: Vec<Book> = serde_json::from_slice(
            &actix_web::test::read_body(resp).await
        ).unwrap();
        assert_eq!(body.len(), 1);

        // Delete
        let req = test::TestRequest::delete().uri(&format!("/books/{}", book_id)).to_request();
        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), 204);

        // Verify deleted
        let req = test::TestRequest::get().uri("/books").to_request();
        let resp = test::call_service(&app, req).await;
        let body: Vec<Book> = serde_json::from_slice(
            &actix_web::test::read_body(resp).await
        ).unwrap();
        assert_eq!(body.len(), 0);
    }
}
