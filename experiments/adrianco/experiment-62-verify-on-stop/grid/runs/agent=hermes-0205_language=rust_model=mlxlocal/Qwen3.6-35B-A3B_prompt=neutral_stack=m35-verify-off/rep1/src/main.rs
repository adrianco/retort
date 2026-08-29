use actix_web::{web, App, HttpResponse, HttpServer, Responder};
use rusqlite::{Connection, Result as SqlResult};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Mutex;

// ── Models ──────────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone)]
struct Book {
    id: String,
    title: String,
    author: String,
    year: i32,
    isbn: String,
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

// ── Database helpers ────────────────────────────────────────────────────────

fn init_db() -> SqlResult<Connection> {
    let conn = Connection::open_in_memory()?;
    conn.execute_batch(
        r#"
        CREATE TABLE IF NOT EXISTS books (
            id    TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year  INTEGER NOT NULL,
            isbn  TEXT NOT NULL
        );
        "#,
    )?;
    Ok(conn)
}

fn db_with<F, T>(pool: &Mutex<Connection>, f: F) -> SqlResult<T>
where
    F: FnOnce(&mut Connection) -> SqlResult<T>,
{
    let mut guard = pool.lock().unwrap();
    f(&mut *guard)
}

fn row_to_book(row: &rusqlite::Row) -> SqlResult<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

// ── Handlers ────────────────────────────────────────────────────────────────

async fn health() -> impl Responder {
    HttpResponse::Ok().json(serde_json::json!({"status": "ok"}))
}

async fn create_book(
    pool: web::Data<Mutex<Connection>>,
    body: actix_web::web::Json<CreateBookRequest>,
) -> HttpResponse {
    let title = match &body.title {
        Some(t) if !t.trim().is_empty() => t.clone(),
        _ => {
            return HttpResponse::BadRequest()
                .json(serde_json::json!({"error": "title is required"}))
        }
    };

    let author = match &body.author {
        Some(a) if !a.trim().is_empty() => a.clone(),
        _ => {
            return HttpResponse::BadRequest()
                .json(serde_json::json!({"error": "author is required"}))
        }
    };

    let year = body.year.unwrap_or(0);
    let isbn = body.isbn.clone().unwrap_or_else(|| String::new());

    let id = uuid::Uuid::new_v4().to_string();

    let pool_ref = pool.get_ref();
    if let Err(e) = db_with(pool_ref, |conn| {
        conn.execute(
            "INSERT INTO books (id, title, author, year, isbn) VALUES (?1, ?2, ?3, ?4, ?5)",
            rusqlite::params![&id, &title, &author, year, &isbn],
        )
    }) {
        return HttpResponse::InternalServerError().json(serde_json::json!({
            "error": format!("database error: {}", e)
        }));
    }

    let book = Book {
        id,
        title,
        author,
        year,
        isbn,
    };

    HttpResponse::Created().json(book)
}

async fn list_books(
    pool: web::Data<Mutex<Connection>>,
    query: web::Query<HashMap<String, String>>,
) -> HttpResponse {
    let pool_ref = pool.get_ref();
    let books: Result<Vec<Book>, _> = if let Some(author_filter) = query.get("author") {
        db_with(pool_ref, |conn| {
            let mut stmt = conn.prepare(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ?1",
            )?;
            let mut rows = stmt.query(rusqlite::params![author_filter])?;
            let mut books = Vec::new();
            while let Some(row) = rows.next()? {
                books.push(row_to_book(row)?);
            }
            Ok(books)
        })
    } else {
        db_with(pool_ref, |conn| {
            let mut stmt = conn.prepare(
                "SELECT id, title, author, year, isbn FROM books",
            )?;
            let mut rows = stmt.query(rusqlite::params![])?;
            let mut books = Vec::new();
            while let Some(row) = rows.next()? {
                books.push(row_to_book(row)?);
            }
            Ok(books)
        })
    };

    match books {
        Ok(b) => HttpResponse::Ok().json(b),
        Err(e) => HttpResponse::InternalServerError().json(serde_json::json!({
            "error": format!("database error: {}", e)
        })),
    }
}

async fn get_book(
    pool: web::Data<Mutex<Connection>>,
    path: web::Path<String>,
) -> HttpResponse {
    let book_id = path.into_inner();
    let pool_ref = pool.get_ref();

    let book: Result<Option<Book>, _> = db_with(pool_ref, |conn| {
        let mut stmt = conn.prepare(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        )?;
        stmt.query_row(rusqlite::params![&book_id], row_to_book).map(Some)
    });

    match book {
        Ok(Some(b)) => HttpResponse::Ok().json(b),
        Ok(None) => HttpResponse::NotFound().json(serde_json::json!({"error": "book not found"})),
        Err(rusqlite::Error::QueryReturnedNoRows) => {
            HttpResponse::NotFound().json(serde_json::json!({"error": "book not found"}))
        }
        Err(e) => HttpResponse::InternalServerError().json(serde_json::json!({
            "error": format!("database error: {}", e)
        })),
    }
}

async fn update_book(
    pool: web::Data<Mutex<Connection>>,
    path: web::Path<String>,
    body: actix_web::web::Json<UpdateBookRequest>,
) -> HttpResponse {
    let book_id = path.into_inner();

    if body.title.is_none()
        && body.author.is_none()
        && body.year.is_none()
        && body.isbn.is_none()
    {
        return HttpResponse::BadRequest()
            .json(serde_json::json!({"error": "at least one field required"}));
    }

    let pool_ref = pool.get_ref();
    let result: Result<Book, _> = db_with(pool_ref, |conn| {
        let existing: Book = conn.query_row(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
            rusqlite::params![&book_id],
            row_to_book,
        )?;

        let new_title = body
            .title
            .as_ref()
            .map(|s| s.as_str())
            .unwrap_or(&existing.title);
        let new_author = body
            .author
            .as_ref()
            .map(|s| s.as_str())
            .unwrap_or(&existing.author);
        let new_year = body.year.unwrap_or(existing.year);
        let new_isbn = body
            .isbn
            .as_ref()
            .map(|s| s.as_str())
            .unwrap_or(&existing.isbn);

        if new_title.trim().is_empty() {
            return Err(rusqlite::Error::InvalidQuery);
        }
        if new_author.trim().is_empty() {
            return Err(rusqlite::Error::InvalidQuery);
        }

        conn.execute(
            "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
            rusqlite::params![new_title, new_author, new_year, new_isbn, &book_id],
        )?;

        Ok(Book {
            id: existing.id,
            title: new_title.to_string(),
            author: new_author.to_string(),
            year: new_year,
            isbn: new_isbn.to_string(),
        })
    });

    match result {
        Ok(b) => HttpResponse::Ok().json(b),
        Err(rusqlite::Error::QueryReturnedNoRows) => {
            HttpResponse::NotFound().json(serde_json::json!({"error": "book not found"}))
        }
        Err(_) => HttpResponse::BadRequest()
            .json(serde_json::json!({"error": "title and author are required"})),
    }
}

async fn delete_book(
    pool: web::Data<Mutex<Connection>>,
    path: web::Path<String>,
) -> HttpResponse {
    let book_id = path.into_inner();
    let pool_ref = pool.get_ref();

    let result: Result<usize, _> = db_with(pool_ref, |conn| {
        conn.execute(
            "DELETE FROM books WHERE id = ?1",
            rusqlite::params![&book_id],
        )
    });

    match result {
        Ok(n) => {
            if n >= 1 {
                HttpResponse::NoContent().finish()
            } else {
                HttpResponse::NotFound().json(serde_json::json!({"error": "book not found"}))
            }
        }
        Err(_) => HttpResponse::InternalServerError().json(serde_json::json!({
            "error": "database error"
        })),
    }
}

// ── App ─────────────────────────────────────────────────────────────────────

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let conn = init_db().expect("Failed to initialize database");
    let pool = web::Data::new(Mutex::new(conn));

    println!("Starting server on http://0.0.0.0:8080");

    HttpServer::new(move || {
        App::new()
            .app_data(pool.clone())
            .route("/health", web::get().to(health))
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

// ── Tests ───────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use actix_web::test;

    fn make_pool() -> web::Data<Mutex<Connection>> {
        web::Data::new(Mutex::new(init_db().unwrap()))
    }

    #[actix_web::test]
    async fn test_health_check() {
        let pool = make_pool();
        let app = test::init_service(
            App::new()
                .app_data(pool)
                .route("/health", web::get().to(health))
                .route("/books", web::post().to(create_book))
                .route("/books", web::get().to(list_books))
                .route("/books/{id}", web::get().to(get_book))
                .route("/books/{id}", web::put().to(update_book))
                .route("/books/{id}", web::delete().to(delete_book)),
        )
        .await;

        let req = test::TestRequest::get().uri("/health").to_request();
        let resp = test::call_service(&app, req).await;

        assert!(resp.status().is_success());
        let body: serde_json::Value = test::read_body_json(resp).await;
        assert_eq!(body["status"], "ok");
    }

    #[actix_web::test]
    async fn test_create_book() {
        let pool = make_pool();
        let app = test::init_service(
            App::new()
                .app_data(pool)
                .route("/health", web::get().to(health))
                .route("/books", web::post().to(create_book))
                .route("/books", web::get().to(list_books))
                .route("/books/{id}", web::get().to(get_book))
                .route("/books/{id}", web::put().to(update_book))
                .route("/books/{id}", web::delete().to(delete_book)),
        )
        .await;

        let req = test::TestRequest::post()
            .uri("/books")
            .set_json(&serde_json::json!({
                "title": "The Rust Programming Language",
                "author": "Steve Klabnik",
                "year": 2018,
                "isbn": "978-1-7185-0044-0"
            }))
            .to_request();

        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), 201);

        let body: Book = test::read_body_json(resp).await;
        assert_eq!(body.title, "The Rust Programming Language");
        assert_eq!(body.author, "Steve Klabnik");
        assert_eq!(body.year, 2018);
        assert!(!body.id.is_empty());
    }

    #[actix_web::test]
    async fn test_create_book_missing_title() {
        let pool = make_pool();
        let app = test::init_service(
            App::new()
                .app_data(pool)
                .route("/health", web::get().to(health))
                .route("/books", web::post().to(create_book))
                .route("/books", web::get().to(list_books))
                .route("/books/{id}", web::get().to(get_book))
                .route("/books/{id}", web::put().to(update_book))
                .route("/books/{id}", web::delete().to(delete_book)),
        )
        .await;

        let req = test::TestRequest::post()
            .uri("/books")
            .set_json(&serde_json::json!({
                "author": "Some Author",
                "year": 2020
            }))
            .to_request();

        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), 400);
    }

    #[actix_web::test]
    async fn test_create_book_missing_author() {
        let pool = make_pool();
        let app = test::init_service(
            App::new()
                .app_data(pool)
                .route("/health", web::get().to(health))
                .route("/books", web::post().to(create_book))
                .route("/books", web::get().to(list_books))
                .route("/books/{id}", web::get().to(get_book))
                .route("/books/{id}", web::put().to(update_book))
                .route("/books/{id}", web::delete().to(delete_book)),
        )
        .await;

        let req = test::TestRequest::post()
            .uri("/books")
            .set_json(&serde_json::json!({
                "title": "Some Book",
                "year": 2020
            }))
            .to_request();

        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), 400);
    }

    #[actix_web::test]
    async fn test_list_books() {
        let pool = make_pool();
        let app = test::init_service(
            App::new()
                .app_data(pool)
                .route("/health", web::get().to(health))
                .route("/books", web::post().to(create_book))
                .route("/books", web::get().to(list_books))
                .route("/books/{id}", web::get().to(get_book))
                .route("/books/{id}", web::put().to(update_book))
                .route("/books/{id}", web::delete().to(delete_book)),
        )
        .await;

        let book1 = serde_json::json!({
            "title": "Book One",
            "author": "Author A",
            "year": 2020,
            "isbn": "111"
        });
        let book2 = serde_json::json!({
            "title": "Book Two",
            "author": "Author A",
            "year": 2021,
            "isbn": "222"
        });
        let book3 = serde_json::json!({
            "title": "Book Three",
            "author": "Author B",
            "year": 2022,
            "isbn": "333"
        });

        for payload in [&book1, &book2, &book3] {
            let req = test::TestRequest::post()
                .uri("/books")
                .set_json(&payload)
                .to_request();
            let resp = test::call_service(&app, req).await;
            assert_eq!(resp.status(), 201);
        }

        let req = test::TestRequest::get().uri("/books").to_request();
        let resp = test::call_service(&app, req).await;
        assert!(resp.status().is_success());
        let books: Vec<Book> = test::read_body_json(resp).await;
        assert_eq!(books.len(), 3);

        let req = test::TestRequest::get()
            .uri("/books?author=Author%20A")
            .to_request();
        let resp = test::call_service(&app, req).await;
        let books: Vec<Book> = test::read_body_json(resp).await;
        assert_eq!(books.len(), 2);
        for book in &books {
            assert_eq!(book.author, "Author A");
        }
    }

    #[actix_web::test]
    async fn test_get_book_not_found() {
        let pool = make_pool();
        let app = test::init_service(
            App::new()
                .app_data(pool)
                .route("/health", web::get().to(health))
                .route("/books", web::post().to(create_book))
                .route("/books", web::get().to(list_books))
                .route("/books/{id}", web::get().to(get_book))
                .route("/books/{id}", web::put().to(update_book))
                .route("/books/{id}", web::delete().to(delete_book)),
        )
        .await;

        let req = test::TestRequest::get()
            .uri("/books/nonexistent-id")
            .to_request();

        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), 404);
    }

    #[actix_web::test]
    async fn test_update_book() {
        let pool = make_pool();
        let app = test::init_service(
            App::new()
                .app_data(pool)
                .route("/health", web::get().to(health))
                .route("/books", web::post().to(create_book))
                .route("/books", web::get().to(list_books))
                .route("/books/{id}", web::get().to(get_book))
                .route("/books/{id}", web::put().to(update_book))
                .route("/books/{id}", web::delete().to(delete_book)),
        )
        .await;

        let create_req = test::TestRequest::post()
            .uri("/books")
            .set_json(&serde_json::json!({
                "title": "Original Title",
                "author": "Original Author",
                "year": 2020,
                "isbn": "123"
            }))
            .to_request();

        let create_resp = test::call_service(&app, create_req).await;
        let created: Book = test::read_body_json(create_resp).await;
        let book_id = created.id;

        let update_req = test::TestRequest::put()
            .uri(&format!("/books/{}", book_id))
            .set_json(&serde_json::json!({
                "title": "Updated Title"
            }))
            .to_request();

        let update_resp = test::call_service(&app, update_req).await;
        assert_eq!(update_resp.status(), 200);

        let updated: Book = test::read_body_json(update_resp).await;
        assert_eq!(updated.title, "Updated Title");
        assert_eq!(updated.author, "Original Author");
        assert_eq!(updated.isbn, "123");
    }

    #[actix_web::test]
    async fn test_delete_book() {
        let pool = make_pool();
        let app = test::init_service(
            App::new()
                .app_data(pool)
                .route("/health", web::get().to(health))
                .route("/books", web::post().to(create_book))
                .route("/books", web::get().to(list_books))
                .route("/books/{id}", web::get().to(get_book))
                .route("/books/{id}", web::put().to(update_book))
                .route("/books/{id}", web::delete().to(delete_book)),
        )
        .await;

        let create_req = test::TestRequest::post()
            .uri("/books")
            .set_json(&serde_json::json!({
                "title": "To Delete",
                "author": "Author",
                "year": 2020,
                "isbn": "999"
            }))
            .to_request();

        let create_resp = test::call_service(&app, create_req).await;
        let created: Book = test::read_body_json(create_resp).await;
        let book_id = created.id;

        let delete_req = test::TestRequest::delete()
            .uri(&format!("/books/{}", book_id))
            .to_request();

        let delete_resp = test::call_service(&app, delete_req).await;
        assert_eq!(delete_resp.status(), 204);

        let get_req = test::TestRequest::get()
            .uri(&format!("/books/{}", book_id))
            .to_request();

        let get_resp = test::call_service(&app, get_req).await;
        assert_eq!(get_resp.status(), 404);
    }

    #[actix_web::test]
    async fn test_delete_book_not_found() {
        let pool = make_pool();
        let app = test::init_service(
            App::new()
                .app_data(pool)
                .route("/health", web::get().to(health))
                .route("/books", web::post().to(create_book))
                .route("/books", web::get().to(list_books))
                .route("/books/{id}", web::get().to(get_book))
                .route("/books/{id}", web::put().to(update_book))
                .route("/books/{id}", web::delete().to(delete_book)),
        )
        .await;

        let req = test::TestRequest::delete()
            .uri("/books/nonexistent")
            .to_request();

        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), 404);
    }
}
