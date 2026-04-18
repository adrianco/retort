use actix_web::{web, App, HttpResponse, HttpServer};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use uuid::Uuid;

#[derive(Debug, Serialize, Deserialize, Clone)]
struct Book {
    id: String,
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
struct CreateBook {
    title: Option<String>,
    author: Option<String>,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
struct UpdateBook {
    title: Option<String>,
    author: Option<String>,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
struct ListQuery {
    author: Option<String>,
}

struct AppState {
    db: Mutex<Connection>,
}

async fn health() -> HttpResponse {
    HttpResponse::Ok().json(serde_json::json!({"status": "ok"}))
}

async fn create_book(
    state: web::Data<AppState>,
    body: web::Json<CreateBook>,
) -> HttpResponse {
    let title = match &body.title {
        Some(t) if !t.trim().is_empty() => t.trim().to_string(),
        _ => {
            return HttpResponse::BadRequest()
                .json(serde_json::json!({"error": "title is required"}));
        }
    };
    let author = match &body.author {
        Some(a) if !a.trim().is_empty() => a.trim().to_string(),
        _ => {
            return HttpResponse::BadRequest()
                .json(serde_json::json!({"error": "author is required"}));
        }
    };

    let db = state.db.lock().unwrap();
    let id = Uuid::new_v4().to_string();

    db.execute(
        "INSERT INTO books (id, title, author, year, isbn) VALUES (?1, ?2, ?3, ?4, ?5)",
        params![id, title, author, body.year, body.isbn],
    )
    .unwrap();

    let book = Book {
        id,
        title,
        author,
        year: body.year,
        isbn: body.isbn.clone(),
    };

    HttpResponse::Created().json(book)
}

async fn list_books(
    state: web::Data<AppState>,
    query: web::Query<ListQuery>,
) -> HttpResponse {
    let db = state.db.lock().unwrap();

    let books: Vec<Book> = if let Some(author_filter) = &query.author {
        let mut stmt = db
            .prepare("SELECT id, title, author, year, isbn FROM books WHERE author LIKE ?1")
            .unwrap();
        stmt.query_map(params![format!("%{}%", author_filter)], |row| {
            Ok(Book {
                id: row.get(0)?,
                title: row.get(1)?,
                author: row.get(2)?,
                year: row.get(3)?,
                isbn: row.get(4)?,
            })
        })
        .unwrap()
        .filter_map(|r| r.ok())
        .collect()
    } else {
        let mut stmt = db
            .prepare("SELECT id, title, author, year, isbn FROM books")
            .unwrap();
        stmt.query_map([], |row| {
            Ok(Book {
                id: row.get(0)?,
                title: row.get(1)?,
                author: row.get(2)?,
                year: row.get(3)?,
                isbn: row.get(4)?,
            })
        })
        .unwrap()
        .filter_map(|r| r.ok())
        .collect()
    };

    HttpResponse::Ok().json(books)
}

async fn get_book(state: web::Data<AppState>, path: web::Path<String>) -> HttpResponse {
    let db = state.db.lock().unwrap();
    let id = path.into_inner();

    let result = db.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        params![id],
        |row| {
            Ok(Book {
                id: row.get(0)?,
                title: row.get(1)?,
                author: row.get(2)?,
                year: row.get(3)?,
                isbn: row.get(4)?,
            })
        },
    );

    match result {
        Ok(book) => HttpResponse::Ok().json(book),
        Err(_) => {
            HttpResponse::NotFound().json(serde_json::json!({"error": "book not found"}))
        }
    }
}

async fn update_book(
    state: web::Data<AppState>,
    path: web::Path<String>,
    body: web::Json<UpdateBook>,
) -> HttpResponse {
    let db = state.db.lock().unwrap();
    let id = path.into_inner();

    let existing = db.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        params![id],
        |row| {
            Ok(Book {
                id: row.get(0)?,
                title: row.get(1)?,
                author: row.get(2)?,
                year: row.get(3)?,
                isbn: row.get(4)?,
            })
        },
    );

    match existing {
        Ok(book) => {
            let title = body
                .title
                .as_deref()
                .map(|t| t.trim().to_string())
                .unwrap_or(book.title.clone());
            let author = body
                .author
                .as_deref()
                .map(|a| a.trim().to_string())
                .unwrap_or(book.author.clone());

            if title.is_empty() {
                return HttpResponse::BadRequest()
                    .json(serde_json::json!({"error": "title cannot be empty"}));
            }
            if author.is_empty() {
                return HttpResponse::BadRequest()
                    .json(serde_json::json!({"error": "author cannot be empty"}));
            }

            let year = body.year.or(book.year);
            let isbn = body.isbn.clone().or(book.isbn);

            db.execute(
                "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
                params![title, author, year, isbn, book.id],
            )
            .unwrap();

            HttpResponse::Ok().json(Book {
                id: book.id,
                title,
                author,
                year,
                isbn,
            })
        }
        Err(_) => {
            HttpResponse::NotFound().json(serde_json::json!({"error": "book not found"}))
        }
    }
}

async fn delete_book(state: web::Data<AppState>, path: web::Path<String>) -> HttpResponse {
    let db = state.db.lock().unwrap();
    let id = path.into_inner();

    let count = db
        .execute("DELETE FROM books WHERE id = ?1", params![id])
        .unwrap();

    if count > 0 {
        HttpResponse::NoContent().finish()
    } else {
        HttpResponse::NotFound().json(serde_json::json!({"error": "book not found"}))
    }
}

fn init_db(conn: &Connection) {
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id   TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year  INTEGER,
            isbn  TEXT
        )",
    )
    .expect("Failed to initialise database schema");
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let conn = Connection::open("books.db").expect("Failed to open database");
    init_db(&conn);

    let data = web::Data::new(AppState {
        db: Mutex::new(conn),
    });

    println!("Listening on http://0.0.0.0:8080");

    HttpServer::new(move || {
        App::new()
            .app_data(data.clone())
            .app_data(
                web::JsonConfig::default()
                    .error_handler(|err, _req| {
                        let msg = format!("{}", err);
                        actix_web::error::InternalError::from_response(
                            err,
                            HttpResponse::BadRequest()
                                .json(serde_json::json!({"error": msg})),
                        )
                        .into()
                    }),
            )
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

#[cfg(test)]
mod tests {
    use super::*;
    use actix_web::{test, web, App};

    fn setup() -> web::Data<AppState> {
        let conn = Connection::open_in_memory().unwrap();
        init_db(&conn);
        web::Data::new(AppState {
            db: Mutex::new(conn),
        })
    }

    fn app_with_data(
        data: web::Data<AppState>,
    ) -> App<
        impl actix_web::dev::ServiceFactory<
            actix_web::dev::ServiceRequest,
            Config = (),
            Response = actix_web::dev::ServiceResponse,
            Error = actix_web::Error,
            InitError = (),
        >,
    > {
        App::new()
            .app_data(data)
            .route("/health", web::get().to(health))
            .route("/books", web::post().to(create_book))
            .route("/books", web::get().to(list_books))
            .route("/books/{id}", web::get().to(get_book))
            .route("/books/{id}", web::put().to(update_book))
            .route("/books/{id}", web::delete().to(delete_book))
    }

    #[actix_web::test]
    async fn test_health_check() {
        let app = test::init_service(App::new().route("/health", web::get().to(health))).await;
        let req = test::TestRequest::get().uri("/health").to_request();
        let resp = test::call_service(&app, req).await;
        assert!(resp.status().is_success());
        let body: serde_json::Value = test::read_body_json(resp).await;
        assert_eq!(body["status"], "ok");
    }

    #[actix_web::test]
    async fn test_create_and_get_book() {
        let data = setup();
        let app = test::init_service(app_with_data(data)).await;

        // Create
        let req = test::TestRequest::post()
            .uri("/books")
            .set_json(serde_json::json!({
                "title": "The Rust Programming Language",
                "author": "Steve Klabnik",
                "year": 2019,
                "isbn": "978-1718500440"
            }))
            .to_request();
        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), 201);
        let created: serde_json::Value = test::read_body_json(resp).await;
        assert_eq!(created["title"], "The Rust Programming Language");
        assert_eq!(created["author"], "Steve Klabnik");
        let id = created["id"].as_str().unwrap().to_string();

        // Get by ID
        let req = test::TestRequest::get()
            .uri(&format!("/books/{}", id))
            .to_request();
        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), 200);
        let fetched: serde_json::Value = test::read_body_json(resp).await;
        assert_eq!(fetched["id"], id);
        assert_eq!(fetched["isbn"], "978-1718500440");
    }

    #[actix_web::test]
    async fn test_create_book_validation() {
        let data = setup();
        let app = test::init_service(app_with_data(data)).await;

        // Missing title
        let req = test::TestRequest::post()
            .uri("/books")
            .set_json(serde_json::json!({"author": "Someone"}))
            .to_request();
        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), 400);

        // Empty author
        let req = test::TestRequest::post()
            .uri("/books")
            .set_json(serde_json::json!({"title": "A Title", "author": ""}))
            .to_request();
        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), 400);
    }

    #[actix_web::test]
    async fn test_list_and_filter_books() {
        let data = setup();
        let app = test::init_service(app_with_data(data)).await;

        // Seed two books
        for (title, author) in [("Book A", "Alice"), ("Book B", "Bob")] {
            let req = test::TestRequest::post()
                .uri("/books")
                .set_json(serde_json::json!({"title": title, "author": author}))
                .to_request();
            test::call_service(&app, req).await;
        }

        // List all
        let req = test::TestRequest::get().uri("/books").to_request();
        let resp = test::call_service(&app, req).await;
        assert!(resp.status().is_success());
        let all: serde_json::Value = test::read_body_json(resp).await;
        assert_eq!(all.as_array().unwrap().len(), 2);

        // Filter by author
        let req = test::TestRequest::get()
            .uri("/books?author=Alice")
            .to_request();
        let resp = test::call_service(&app, req).await;
        let filtered: serde_json::Value = test::read_body_json(resp).await;
        assert_eq!(filtered.as_array().unwrap().len(), 1);
        assert_eq!(filtered[0]["author"], "Alice");
    }

    #[actix_web::test]
    async fn test_update_book() {
        let data = setup();
        let app = test::init_service(app_with_data(data)).await;

        // Create
        let req = test::TestRequest::post()
            .uri("/books")
            .set_json(serde_json::json!({"title": "Old Title", "author": "Old Author"}))
            .to_request();
        let resp = test::call_service(&app, req).await;
        let created: serde_json::Value = test::read_body_json(resp).await;
        let id = created["id"].as_str().unwrap().to_string();

        // Update
        let req = test::TestRequest::put()
            .uri(&format!("/books/{}", id))
            .set_json(serde_json::json!({"title": "New Title"}))
            .to_request();
        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), 200);
        let updated: serde_json::Value = test::read_body_json(resp).await;
        assert_eq!(updated["title"], "New Title");
        assert_eq!(updated["author"], "Old Author"); // unchanged
    }

    #[actix_web::test]
    async fn test_delete_book() {
        let data = setup();
        let app = test::init_service(app_with_data(data)).await;

        // Create
        let req = test::TestRequest::post()
            .uri("/books")
            .set_json(serde_json::json!({"title": "To Delete", "author": "Author"}))
            .to_request();
        let resp = test::call_service(&app, req).await;
        let created: serde_json::Value = test::read_body_json(resp).await;
        let id = created["id"].as_str().unwrap().to_string();

        // Delete
        let req = test::TestRequest::delete()
            .uri(&format!("/books/{}", id))
            .to_request();
        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), 204);

        // Confirm gone
        let req = test::TestRequest::get()
            .uri(&format!("/books/{}", id))
            .to_request();
        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), 404);
    }

    #[actix_web::test]
    async fn test_not_found() {
        let data = setup();
        let app = test::init_service(app_with_data(data)).await;

        let req = test::TestRequest::get()
            .uri("/books/does-not-exist")
            .to_request();
        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), 404);
    }
}
