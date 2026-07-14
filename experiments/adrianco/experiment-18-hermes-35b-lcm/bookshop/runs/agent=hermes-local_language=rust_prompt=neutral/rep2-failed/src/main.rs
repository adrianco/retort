mod db;
mod models;

use actix_web::{web, App, HttpResponse, HttpServer, Result};
use models::{BookCreate, ErrorResponse, HealthResponse};
use std::collections::HashMap;

// ─── Handlers ────────────────────────────────────────────────────────────

async fn create_book(
    body: actix_web::web::Json<BookCreate>,
    data: web::Data<db::DbState>,
) -> Result<HttpResponse> {
    let validated = match body.validate() {
        Ok(v) => v,
        Err((error, _field)) => {
            return Ok(HttpResponse::BadRequest().json(ErrorResponse { error }));
        }
    };

    let book = data.create_book(
        &validated.title.unwrap(),
        &validated.author.unwrap(),
        validated.year,
        &validated.isbn,
    )
    .map_err(actix_web::error::ErrorInternalServerError);

    Ok(HttpResponse::Created().json(&book?))
}

async fn list_books(
    query: web::Query<HashMap<String, String>>,
    data: web::Data<db::DbState>,
) -> Result<HttpResponse> {
    let books = match query.get("author") {
        Some(a) => data
            .list_books_by_author(a)
            .map_err(actix_web::error::ErrorInternalServerError),
        None => data
            .list_books()
            .map_err(actix_web::error::ErrorInternalServerError),
    };

    Ok(HttpResponse::Ok().json(&books?))
}

async fn get_book(
    book_id: web::Path<i64>,
    data: web::Data<db::DbState>,
) -> Result<HttpResponse> {
    let book = data
        .get_book(*book_id)
        .map_err(actix_web::error::ErrorInternalServerError);

    match book? {
        Some(b) => Ok(HttpResponse::Ok().json(&b)),
        None => Ok(HttpResponse::NotFound().json(ErrorResponse {
            error: "Book not found".to_string(),
        })),
    }
}

async fn update_book(
    book_id: web::Path<i64>,
    body: actix_web::web::Json<BookCreate>,
    data: web::Data<db::DbState>,
) -> Result<HttpResponse> {
    let validated = match body.validate() {
        Ok(v) => v,
        Err((error, _field)) => {
            return Ok(HttpResponse::BadRequest().json(ErrorResponse { error }));
        }
    };

    let book = data
        .update_book(
            *book_id,
            &validated.title.unwrap(),
            &validated.author.unwrap(),
            validated.year,
            &validated.isbn,
        )
        .map_err(actix_web::error::ErrorInternalServerError);

    match book? {
        Some(b) => Ok(HttpResponse::Ok().json(&b)),
        None => Ok(HttpResponse::NotFound().json(ErrorResponse {
            error: "Book not found".to_string(),
        })),
    }
}

async fn delete_book(
    book_id: web::Path<i64>,
    data: web::Data<db::DbState>,
) -> Result<HttpResponse> {
    let deleted = data
        .delete_book(*book_id)
        .map_err(actix_web::error::ErrorInternalServerError);

    if deleted? {
        Ok(HttpResponse::NoContent().finish())
    } else {
        Ok(HttpResponse::NotFound().json(ErrorResponse {
            error: "Book not found".to_string(),
        }))
    }
}

async fn health_check() -> HttpResponse {
    HttpResponse::Ok().json(HealthResponse {
        status: "ok".to_string(),
    })
}

// ─── Entry point ─────────────────────────────────────────────────────────

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let db = db::DbState::new().unwrap();
    println!("Starting book API server on http://0.0.0.0:8080");

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

// ─── Tests ───────────────────────────────────────────────────────────────

fn make_app() -> impl Fn() -> App {
    let db = db::DbState::new().unwrap();
    move || {
        App::new()
            .app_data(web::Data::new(db.clone()))
            .route("/health", web::get().to(health_check))
            .route("/books", web::post().to(create_book))
            .route("/books", web::get().to(list_books))
            .route("/books/{id}", web::get().to(get_book))
            .route("/books/{id}", web::put().to(update_book))
            .route("/books/{id}", web::delete().to(delete_book))
    }
}

fn app_factory() -> impl Fn() -> App + Send + Clone + 'static {
    let db = db::DbState::new().unwrap();
    move || {
        App::new()
            .app_data(web::Data::new(db.clone()))
            .route("/health", web::get().to(health_check))
            .route("/books", web::post().to(create_book))
            .route("/books", web::get().to(list_books))
            .route("/books/{id}", web::get().to(get_book))
            .route("/books/{id}", web::put().to(update_book))
            .route("/books/{id}", web::delete().to(delete_book))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use actix_test::start;
    use actix_web::test;
    use serde_json::json;

    async fn create_test_book(srv: &actix_test::TestServer, title: &str, author: &str, year: i32) -> i64 {
        let body = json!({
            "title": title,
            "author": author,
            "year": year
        });
        let resp = srv
            .post("/books")
            .send_json(&body)
            .await
            .unwrap();
        assert_eq!(resp.status().as_u16(), 201);
        let book: Book = resp.json().await.unwrap();
        book.id
    }

    // 1. CREATE book — success with 201 and correct body
    #[actix_web::test]
    async fn test_create_book_returns_201_with_body() {
        let srv = start(app_factory());
        let body = json!({
            "title": "The Rust Programming Language",
            "author": "Steve Klabnik",
            "year": 2023,
            "isbn": "978-1-7185-0044-0"
        });
        let req = srv.post("/books");
        let resp = req.send_json(&body).await.unwrap();
        assert_eq!(resp.status().as_u16(), 201);

        let book: Book = resp.json().await.unwrap();
        assert_eq!(book.title, "The Rust Programming Language");
        assert_eq!(book.author, "Steve Klabnik");
        assert_eq!(book.year, Some(2023));
        assert_eq!(book.isbn, Some("978-1-7185-0044-0".to_string()));
        assert!(book.id > 0);
    }

    // 2. CREATE — missing title returns 400
    #[actix_web::test]
    async fn test_create_book_rejects_missing_title() {
        let srv = start(app_factory());
        let body = json!({"author": "Author", "year": 2020});
        let resp = srv
            .post("/books")
            .send_json(&body)
            .await
            .unwrap();
        assert_eq!(resp.status().as_u16(), 400);
    }

    // 3. CREATE — missing author returns 400
    #[actix_web::test]
    async fn test_create_book_rejects_missing_author() {
        let srv = start(app_factory());
        let body = json!({"title": "Title", "year": 2020});
        let resp = srv
            .post("/books")
            .send_json(&body)
            .await
            .unwrap();
        assert_eq!(resp.status().as_u16(), 400);
    }

    // 4. CREATE — empty/whitespace title returns 400
    #[actix_web::test]
    async fn test_create_book_rejects_empty_title() {
        let srv = start(app_factory());
        let body = json!({"title": "   ", "author": "A", "year": 2020});
        let resp = srv
            .post("/books")
            .send_json(&body)
            .await
            .unwrap();
        assert_eq!(resp.status().as_u16(), 400);
    }

    // 5. CREATE — empty/whitespace author returns 400
    #[actix_web::test]
    async fn test_create_book_rejects_empty_author() {
        let srv = start(app_factory());
        let body = json!({"title": "T", "author": "   ", "year": 2020});
        let resp = srv
            .post("/books")
            .send_json(&body)
            .await
            .unwrap();
        assert_eq!(resp.status().as_u16(), 400);
    }

    // 6. LIST all books
    #[actix_web::test]
    async fn test_list_books_returns_all() {
        let srv = start(app_factory());
        srv.post("/books")
            .send_json(&json!({"title": "A", "author": "X", "year": 2020}))
            .await
            .unwrap();
        srv.post("/books")
            .send_json(&json!({"title": "B", "author": "Y", "year": 2021}))
            .await
            .unwrap();

        let resp = srv.get("/books").send().await.unwrap();
        assert_eq!(resp.status().as_u16(), 200);
        let books: Vec<Book> = resp.json().await.unwrap();
        assert_eq!(books.len(), 2);
    }

    // 7. LIST filtered by author query param
    #[actix_web::test]
    async fn test_list_books_filters_by_author() {
        let srv = start(app_factory());
        srv.post("/books")
            .send_json(&json!({"title": "A1", "author": "Alice", "year": 2020}))
            .await
            .unwrap();
        srv.post("/books")
            .send_json(&json!({"title": "B1", "author": "Bob", "year": 2021}))
            .await
            .unwrap();

        let resp = srv
            .get("/books?author=Bob")
            .send()
            .await
            .unwrap();
        assert_eq!(resp.status().as_u16(), 200);
        let books: Vec<Book> = resp.json().await.unwrap();
        assert_eq!(books.len(), 1);
        assert_eq!(books[0].author, "Bob");
    }

    // 8. GET single book by id
    #[actix_web::test]
    async fn test_get_single_book() {
        let srv = start(app_factory());
        let id = create_test_book(&srv, "Get Me", "Author X", 2022).await;

        let resp = srv
            .get(&format!("/books/{}", id))
            .send()
            .await
            .unwrap();
        assert_eq!(resp.status().as_u16(), 200);

        let book: Book = resp.json().await.unwrap();
        assert_eq!(book.id, id);
        assert_eq!(book.title, "Get Me");
    }

    // 9. GET nonexistent book — 404
    #[actix_web::test]
    async fn test_get_nonexistent_book_returns_404() {
        let srv = start(app_factory());
        let resp = srv
            .get("/books/9999")
            .send()
            .await
            .unwrap();
        assert_eq!(resp.status().as_u16(), 404);
    }

    // 10. PUT update existing book
    #[actix_web::test]
    async fn test_update_book() {
        let srv = start(app_factory());
        let id = create_test_book(&srv, "Old Title", "Old Author", 2020).await;

        let updated = json!({
            "title": "New Title",
            "author": "New Author",
            "year": 2025,
            "isbn": "123-456"
        });
        let resp = srv
            .put(&format!("/books/{}", id))
            .send_json(&updated)
            .await
            .unwrap();
        assert_eq!(resp.status().as_u16(), 200);

        let book: Book = resp.json().await.unwrap();
        assert_eq!(book.title, "New Title");
        assert_eq!(book.author, "New Author");
        assert_eq!(book.year, Some(2025));
        assert_eq!(book.isbn, Some("123-456".to_string()));
    }

    // 11. PUT update nonexistent book — 404
    #[actix_web::test]
    async fn test_update_nonexistent_book_returns_404() {
        let srv = start(app_factory());
        let body = json!({"title": "X", "author": "Y", "year": 2020});
        let resp = srv
            .put("/books/9999")
            .send_json(&body)
            .await
            .unwrap();
        assert_eq!(resp.status().as_u16(), 404);
    }

    // 12. DELETE existing book — 204
    #[actix_web::test]
    async fn test_delete_book() {
        let srv = start(app_factory());
        let id = create_test_book(&srv, "Delete Me", "Author", 2020).await;

        let resp = srv
            .delete(&format!("/books/{}", id))
            .send()
            .await
            .unwrap();
        assert_eq!(resp.status().as_u16(), 204);

        // Verify gone
        let resp = srv
            .get(&format!("/books/{}", id))
            .send()
            .await
            .unwrap();
        assert_eq!(resp.status().as_u16(), 404);
    }

    // 13. DELETE nonexistent book — 404
    #[actix_web::test]
    async fn test_delete_nonexistent_book_returns_404() {
        let srv = start(app_factory());
        let resp = srv
            .delete("/books/9999")
            .send()
            .await
            .unwrap();
        assert_eq!(resp.status().as_u16(), 404);
    }

    // 14. Health check endpoint
    #[actix_web::test]
    async fn test_health_check() {
        let srv = start(app_factory());
        let resp = srv
            .get("/health")
            .send()
            .await
            .unwrap();
        assert_eq!(resp.status().as_u16(), 200);

        let body: HealthResponse = resp.json().await.unwrap();
        assert_eq!(body.status, "ok");
    }

    // 15. Full CRUD lifecycle
    #[actix_web::test]
    async fn test_full_crud_workflow() {
        let srv = start(app_factory());

        // CREATE
        let id = create_test_book(&srv, "Full Test Book", "Test Author", 2023).await;
        assert!(id > 0);

        // READ
        let resp = srv
            .get(&format!("/books/{}", id))
            .send()
            .await
            .unwrap();
        assert_eq!(resp.status().as_u16(), 200);

        // UPDATE
        let updated = json!({
            "title": "Updated Full Test Book",
            "author": "Updated Author",
            "year": 2024,
            "isbn": "999"
        });
        let resp = srv
            .put(&format!("/books/{}", id))
            .send_json(&updated)
            .await
            .unwrap();
        assert_eq!(resp.status().as_u16(), 200);
        let book: Book = resp.json().await.unwrap();
        assert_eq!(book.title, "Updated Full Test Book");

        // DELETE
        let resp = srv
            .delete(&format!("/books/{}", id))
            .send()
            .await
            .unwrap();
        assert_eq!(resp.status().as_u16(), 204);
    }
}
