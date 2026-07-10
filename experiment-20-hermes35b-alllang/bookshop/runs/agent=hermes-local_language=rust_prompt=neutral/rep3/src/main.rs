use actix_web::{web, App, HttpServer, HttpResponse};
use rusqlite::{Connection, Result as SqliteResult, params};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

// -- Models --

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Book {
    id: Option<i64>,
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
struct CreateBookRequest {
    title: Option<String>,
    author: Option<String>,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
struct UpdateBookRequest {
    title: Option<String>,
    author: Option<String>,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Debug, Serialize)]
struct ErrorResponse {
    error: String,
}

// -- Database --

struct Db {
    conn: Arc<Mutex<Connection>>,
}

impl Clone for Db {
    fn clone(&self) -> Self {
        Db {
            conn: self.conn.clone(),
        }
    }
}

impl Db {
    fn init(db_path: &str) -> SqliteResult<Self> {
        let conn = Connection::open(db_path)?;
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS books (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year  INTEGER,
                isbn  TEXT
            );",
        )?;
        Ok(Db {
            conn: Arc::new(Mutex::new(conn)),
        })
    }

    fn insert(
        &self,
        title: &str,
        author: &str,
        year: Option<i32>,
        isbn: Option<&str>,
    ) -> SqliteResult<i64> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare(
            "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        )?;
        Ok(stmt.insert(params![title, author, year, isbn])?)
    }

    fn find_by_id(&self, id: i64) -> SqliteResult<Option<Book>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        )?;
        let mut rows = stmt.query(params![id])?;
        match rows.next()? {
            Some(row) => Ok(Some(Book {
                id: Some(row.get(0)?),
                title: row.get(1)?,
                author: row.get(2)?,
                year: row.get(3)?,
                isbn: row.get(4)?,
            })),
            None => Ok(None),
        }
    }

    fn list(&self, author_filter: Option<&str>) -> SqliteResult<Vec<Book>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = if let Some(_a) = author_filter {
            conn.prepare(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ?1",
            )?
        } else {
            conn.prepare(
                "SELECT id, title, author, year, isbn FROM books",
            )?
        };
        let mut rows = if author_filter.is_some() {
            stmt.query(params![author_filter.unwrap()])?
        } else {
            stmt.query(params![])?
        };
        let mut result = Vec::new();
        while let Some(row) = rows.next()? {
            result.push(Book {
                id: Some(row.get(0)?),
                title: row.get(1)?,
                author: row.get(2)?,
                year: row.get(3)?,
                isbn: row.get(4)?,
            });
        }
        Ok(result)
    }

    fn update(
        &self,
        id: i64,
        title: Option<&str>,
        author: Option<&str>,
        year: Option<i32>,
        isbn: Option<&str>,
    ) -> SqliteResult<usize> {
        let conn = self.conn.lock().unwrap();
        let mut updates: Vec<String> = Vec::new();
        let mut params_list: Vec<Box<dyn rusqlite::ToSql>> = Vec::new();

        if let Some(t) = title {
            updates.push("title = ?".to_string());
            params_list.push(Box::new(t));
        }
        if let Some(a) = author {
            updates.push("author = ?".to_string());
            params_list.push(Box::new(a));
        }
        if year.is_some() {
            updates.push("year = ?".to_string());
            params_list.push(Box::new(year));
        }
        if isbn.is_some() {
            updates.push("isbn = ?".to_string());
            params_list.push(Box::new(isbn));
        }

        if updates.is_empty() {
            return Ok(0);
        }

        params_list.push(Box::new(id));

        let sql = format!("UPDATE books SET {} WHERE id = ?", updates.join(", "));
        let refs: Vec<&dyn rusqlite::ToSql> = params_list.iter().map(|v| v.as_ref()).collect();
        let count = conn.execute(&sql, &refs[..])?;
        Ok(count)
    }

    fn delete(&self, id: i64) -> SqliteResult<usize> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("DELETE FROM books WHERE id = ?1")?;
        Ok(stmt.execute(params![id])?)
    }
}

// -- Handlers --

async fn health() -> HttpResponse {
    HttpResponse::Ok().json(serde_json::json!({ "status": "ok" }))
}

async fn create_book(
    db: web::Data<Db>,
    body: web::Json<CreateBookRequest>,
) -> HttpResponse {
    let title = match &body.title {
        Some(t) if !t.trim().is_empty() => t.clone(),
        _ => return HttpResponse::BadRequest().json(ErrorResponse {
            error: "title is required".to_string(),
        }),
    };

    let author = match &body.author {
        Some(a) if !a.trim().is_empty() => a.clone(),
        _ => return HttpResponse::BadRequest().json(ErrorResponse {
            error: "author is required".to_string(),
        }),
    };

    let id = match db.insert(&title, &author, body.year, body.isbn.as_deref()) {
        Ok(id) => id,
        Err(e) => return HttpResponse::InternalServerError().json(ErrorResponse {
            error: format!("database error: {}", e),
        }),
    };

    match db.find_by_id(id) {
        Ok(Some(book)) => HttpResponse::Created().json(&book),
        Ok(None) => HttpResponse::InternalServerError().json(ErrorResponse {
            error: "failed to retrieve created book".to_string(),
        }),
        Err(e) => HttpResponse::InternalServerError().json(ErrorResponse {
            error: format!("database error: {}", e),
        }),
    }
}

async fn list_books(
    db: web::Data<Db>,
    query: web::Query<HashMap<String, String>>,
) -> HttpResponse {
    let author_filter = query.get("author").map(|s| s.as_str());
    match db.list(author_filter) {
        Ok(books) => HttpResponse::Ok().json(&books),
        Err(e) => HttpResponse::InternalServerError().json(ErrorResponse {
            error: format!("database error: {}", e),
        }),
    }
}

async fn get_book(db: web::Data<Db>, path: web::Path<i64>) -> HttpResponse {
    let id = path.into_inner();
    match db.find_by_id(id) {
        Ok(Some(book)) => HttpResponse::Ok().json(&book),
        Ok(None) => HttpResponse::NotFound().json(ErrorResponse {
            error: "book not found".to_string(),
        }),
        Err(e) => HttpResponse::InternalServerError().json(ErrorResponse {
            error: format!("database error: {}", e),
        }),
    }
}

async fn update_book(
    db: web::Data<Db>,
    path: web::Path<i64>,
    body: web::Json<UpdateBookRequest>,
) -> HttpResponse {
    let id = path.into_inner();

    if db.find_by_id(id).unwrap().is_none() {
        return HttpResponse::NotFound().json(ErrorResponse {
            error: "book not found".to_string(),
        });
    }

    let rows_updated = match db.update(
        id,
        body.title.as_deref(),
        body.author.as_deref(),
        body.year,
        body.isbn.as_deref(),
    ) {
        Ok(n) => n,
        Err(e) => return HttpResponse::InternalServerError().json(ErrorResponse {
            error: format!("database error: {}", e),
        }),
    };

    if rows_updated == 0 {
        return HttpResponse::BadRequest().json(ErrorResponse {
            error: "no fields to update".to_string(),
        });
    }

    match db.find_by_id(id) {
        Ok(Some(book)) => HttpResponse::Ok().json(&book),
        Ok(None) => HttpResponse::InternalServerError().json(ErrorResponse {
            error: "book disappeared after update".to_string(),
        }),
        Err(e) => HttpResponse::InternalServerError().json(ErrorResponse {
            error: format!("database error: {}", e),
        }),
    }
}

async fn delete_book(db: web::Data<Db>, path: web::Path<i64>) -> HttpResponse {
    let id = path.into_inner();

    if db.find_by_id(id).unwrap().is_none() {
        return HttpResponse::NotFound().json(ErrorResponse {
            error: "book not found".to_string(),
        });
    }

    match db.delete(id) {
        Ok(1) => HttpResponse::NoContent().finish(),
        Ok(_) => HttpResponse::NotFound().json(ErrorResponse {
            error: "book not found".to_string(),
        }),
        Err(e) => HttpResponse::InternalServerError().json(ErrorResponse {
            error: format!("database error: {}", e),
        }),
    }
}

// -- Tests --

#[cfg(test)]
mod tests {
    use super::*;

    fn setup_db(suffix: &str) -> (Db, std::path::PathBuf) {
        let tmp = std::env::temp_dir()
            .join(format!("book_api_unit_test_{}.db", suffix));
        let _ = std::fs::remove_file(&tmp);
        let db = Db::init(tmp.to_str().unwrap()).unwrap();
        (db, tmp)
    }

    #[test]
    fn test_create_and_find_book() {
        let (db, _tmp) = setup_db("create_find");

        let id = db.insert(
            "The Rust Programming Language",
            "Steve Klabnik",
            Some(2019),
            Some("978-1-7185-0044-4"),
        ).unwrap();

        let book = db.find_by_id(id).unwrap().unwrap();
        assert_eq!(book.title, "The Rust Programming Language");
        assert_eq!(book.author, "Steve Klabnik");
        assert_eq!(book.year, Some(2019));
        assert_eq!(book.isbn, Some("978-1-7185-0044-4".to_string()));
        assert_eq!(book.id, Some(id));
    }

    #[test]
    fn test_update_book() {
        let (db, _tmp) = setup_db("update");

        let id = db.insert("Old Title", "Old Author", Some(2000), None).unwrap();

        let rows = db.update(id, Some("New Title"), None, Some(2025), None).unwrap();
        assert_eq!(rows, 1);

        let book = db.find_by_id(id).unwrap().unwrap();
        assert_eq!(book.title, "New Title");
        assert_eq!(book.author, "Old Author");
        assert_eq!(book.year, Some(2025));
    }

    #[test]
    fn test_delete_book() {
        let (db, _tmp) = setup_db("delete");

        let id = db.insert("To Delete", "Author", None, None).unwrap();

        let rows = db.delete(id).unwrap();
        assert_eq!(rows, 1);

        let result = db.find_by_id(id).unwrap();
        assert!(result.is_none());
    }

    #[test]
    fn test_list_books_empty() {
        let (db, _tmp) = setup_db("list_empty");
        let books = db.list(None).unwrap();
        assert!(books.is_empty());
    }

    #[test]
    fn test_list_books_filter() {
        let (db, _tmp) = setup_db("list_filter");

        db.insert("Book A", "Author X", Some(2020), None).unwrap();
        db.insert("Book B", "Author Y", Some(2021), None).unwrap();
        db.insert("Book C", "Author X", Some(2022), None).unwrap();

        let all = db.list(None).unwrap();
        assert_eq!(all.len(), 3);

        let filtered = db.list(Some("Author X")).unwrap();
        assert_eq!(filtered.len(), 2);
        for book in &filtered {
            assert_eq!(book.author, "Author X");
        }
    }

    #[test]
    fn test_delete_nonexistent_book() {
        let (db, _tmp) = setup_db("del_nonexist");
        let rows = db.delete(9999).unwrap();
        assert_eq!(rows, 0);
    }

    #[test]
    fn test_update_nonexistent_book() {
        let (db, _tmp) = setup_db("upd_nonexist");
        let rows = db.update(9999, Some("New"), None, None, None).unwrap();
        assert_eq!(rows, 0);
    }

    #[test]
    fn test_cloning_db_shares_connection() {
        let (db1, _tmp) = setup_db("clone");
        db1.insert("Shared", "Author", None, None).unwrap();

        let db2 = db1.clone();
        let books = db2.list(None).unwrap();
        assert_eq!(books.len(), 1);
        assert_eq!(books[0].title, "Shared");
    }

    #[test]
    fn test_book_serialization() {
        let book = Book {
            id: Some(1),
            title: "Test Book".to_string(),
            author: "Test Author".to_string(),
            year: Some(2024),
            isbn: Some("123".to_string()),
        };

        let json = serde_json::to_string(&book).unwrap();
        assert!(json.contains("Test Book"));
        assert!(json.contains("Test Author"));

        let deserialized: Book = serde_json::from_str(&json).unwrap();
        assert_eq!(deserialized.title, "Test Book");
        assert_eq!(deserialized.author, "Test Author");
    }

    #[test]
    fn test_error_response_serialization() {
        let err = ErrorResponse {
            error: "Not found".to_string(),
        };
        let json = serde_json::to_string(&err).unwrap();
        assert!(json.contains("Not found"));
    }
}

// -- Main --

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let tmp = std::env::temp_dir().join("book_api_dev.db");
    let db = Db::init(tmp.to_str().unwrap()).expect("Failed to initialize database");

    println!("Starting server on http://127.0.0.1:8080");
    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(db.clone()))
            .route("/health", web::get().to(health))
            .route("/books", web::get().to(list_books))
            .route("/books", web::post().to(create_book))
            .route("/books/{id}", web::get().to(get_book))
            .route("/books/{id}", web::put().to(update_book))
            .route("/books/{id}", web::delete().to(delete_book))
    })
    .bind("127.0.0.1:8080")?
    .run()
    .await
}
