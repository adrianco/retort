use actix_web::{web, App, HttpServer, HttpResponse, Responder};
use serde_json::json;
use std::collections::HashMap;
use std::sync::Mutex;

mod models;
mod database;

type DbState = Mutex<rusqlite::Connection>;

async fn health_check() -> impl Responder {
    HttpResponse::Ok().json(json!({"status": "healthy"}))
}

async fn create_book(
    db: web::Data<DbState>,
    body: web::Json<models::CreateBookRequest>,
) -> impl Responder {
    let conn = db.lock().unwrap();
    match database::create_book(&conn, &body) {
        Ok(book) => HttpResponse::Created().json(book),
        Err(msg) => HttpResponse::BadRequest().json(json!({"error": msg})),
    }
}

async fn list_books(
    db: web::Data<DbState>,
    author: web::Query<HashMap<String, String>>,
) -> impl Responder {
    let conn = db.lock().unwrap();
    let author_filter = author.get("author").map(|s| s.as_str());
    match database::list_books(&conn, author_filter) {
        Ok(books) => HttpResponse::Ok().json(books),
        Err(msg) => HttpResponse::InternalServerError().json(json!({"error": msg})),
    }
}

async fn get_book(db: web::Data<DbState>, path: web::Path<String>) -> impl Responder {
    let conn = db.lock().unwrap();
    let book_id = path.into_inner();
    match database::get_book_by_id(&conn, &book_id) {
        Ok(book) => HttpResponse::Ok().json(book),
        Err(msg) => HttpResponse::NotFound().json(json!({"error": msg})),
    }
}

async fn update_book(
    db: web::Data<DbState>,
    path: web::Path<String>,
    body: web::Json<models::UpdateBookRequest>,
) -> impl Responder {
    let conn = db.lock().unwrap();
    let book_id = path.into_inner();
    match database::update_book(&conn, &book_id, &body) {
        Ok(book) => HttpResponse::Ok().json(book),
        Err(msg) => {
            if msg.contains("not found") {
                HttpResponse::NotFound().json(json!({"error": msg}))
            } else {
                HttpResponse::BadRequest().json(json!({"error": msg}))
            }
        }
    }
}

async fn delete_book(db: web::Data<DbState>, path: web::Path<String>) -> impl Responder {
    let conn = db.lock().unwrap();
    let book_id = path.into_inner();
    match database::delete_book(&conn, &book_id) {
        Ok(()) => HttpResponse::NoContent().finish(),
        Err(msg) => HttpResponse::NotFound().json(json!({"error": msg})),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();

    let db = rusqlite::Connection::open_in_memory().unwrap();
    models::create_connection("in-memory").ok();

    let db_data = web::Data::new(Mutex::new(db));

    let server = HttpServer::new(move || {
        App::new()
            .app_data(web::Data::clone(&db_data))
            .route("/health", web::get().to(health_check))
            .route("/books", web::get().to(list_books))
            .route("/books", web::post().to(create_book))
            .route("/books/{id}", web::get().to(get_book))
            .route("/books/{id}", web::put().to(update_book))
            .route("/books/{id}", web::delete().to(delete_book))
    })
    .bind("127.0.0.1:8080")?;

    println!("Server running at http://127.0.0.1:8080");
    server.run().await
}

#[cfg(test)]
mod tests {
    use super::*;
    use actix_web::test;
    use actix_web::http::StatusCode;
    use serde_json::json;

    fn create_db() -> rusqlite::Connection {
        let conn = rusqlite::Connection::open_in_memory().unwrap();
        conn.execute_batch(models::TABLE_DEF).unwrap();
        conn
    }

    #[actix_web::test]
    async fn test_health_check() {
        let db = create_db();
        let db_data = web::Data::new(Mutex::new(db));

        let app = test::init_service(
            App::new()
                .app_data(db_data)
                .route("/health", web::get().to(health_check))
                .route("/books", web::get().to(list_books))
                .route("/books", web::post().to(create_book))
                .route("/books/{id}", web::get().to(get_book))
                .route("/books/{id}", web::put().to(update_book))
                .route("/books/{id}", web::delete().to(delete_book)),
        )
        .await;

        let req = test::TestRequest::get().uri("/health").to_request();
        let resp = test::call_service(&app, req).await;

        assert_eq!(resp.status(), StatusCode::OK);
        let body: serde_json::Value = test::read_body_json(resp).await;
        assert_eq!(body["status"], "healthy");
    }

    #[actix_web::test]
    async fn test_create_book() {
        let db = create_db();
        let db_data = web::Data::new(Mutex::new(db));

        let app = test::init_service(
            App::new()
                .app_data(db_data)
                .route("/health", web::get().to(health_check))
                .route("/books", web::get().to(list_books))
                .route("/books", web::post().to(create_book))
                .route("/books/{id}", web::get().to(get_book))
                .route("/books/{id}", web::put().to(update_book))
                .route("/books/{id}", web::delete().to(delete_book)),
        )
        .await;

        let payload = json!({
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "year": 1925,
            "isbn": "978-0743273565"
        });

        let req = test::TestRequest::post()
            .uri("/books")
            .set_json(payload)
            .to_request();

        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), StatusCode::CREATED);

        let body: serde_json::Value = test::read_body_json(resp).await;
        assert_eq!(body["title"], "The Great Gatsby");
        assert_eq!(body["author"], "F. Scott Fitzgerald");
        assert_eq!(body["year"], 1925);
        assert_eq!(body["isbn"], "978-0743273565");
        assert!(!body["id"].is_null());
    }

    #[actix_web::test]
    async fn test_create_book_missing_title_returns_400() {
        let db = create_db();
        let db_data = web::Data::new(Mutex::new(db));

        let app = test::init_service(
            App::new()
                .app_data(db_data)
                .route("/health", web::get().to(health_check))
                .route("/books", web::get().to(list_books))
                .route("/books", web::post().to(create_book))
                .route("/books/{id}", web::get().to(get_book))
                .route("/books/{id}", web::put().to(update_book))
                .route("/books/{id}", web::delete().to(delete_book)),
        )
        .await;

        let payload = json!({
            "author": "George Orwell",
            "year": 1949
        });

        let req = test::TestRequest::post()
            .uri("/books")
            .set_json(payload)
            .to_request();

        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), StatusCode::BAD_REQUEST);

        let body: serde_json::Value = test::read_body_json(resp).await;
        assert_eq!(body["error"], "title is required");
    }

    #[actix_web::test]
    async fn test_create_book_missing_author_returns_400() {
        let db = create_db();
        let db_data = web::Data::new(Mutex::new(db));

        let app = test::init_service(
            App::new()
                .app_data(db_data)
                .route("/health", web::get().to(health_check))
                .route("/books", web::get().to(list_books))
                .route("/books", web::post().to(create_book))
                .route("/books/{id}", web::get().to(get_book))
                .route("/books/{id}", web::put().to(update_book))
                .route("/books/{id}", web::delete().to(delete_book)),
        )
        .await;

        let payload = json!({
            "title": "1984"
        });

        let req = test::TestRequest::post()
            .uri("/books")
            .set_json(payload)
            .to_request();

        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), StatusCode::BAD_REQUEST);

        let body: serde_json::Value = test::read_body_json(resp).await;
        assert_eq!(body["error"], "author is required");
    }

    #[actix_web::test]
    async fn test_list_books_empty() {
        let db = create_db();
        let db_data = web::Data::new(Mutex::new(db));

        let app = test::init_service(
            App::new()
                .app_data(db_data)
                .route("/health", web::get().to(health_check))
                .route("/books", web::get().to(list_books))
                .route("/books", web::post().to(create_book))
                .route("/books/{id}", web::get().to(get_book))
                .route("/books/{id}", web::put().to(update_book))
                .route("/books/{id}", web::delete().to(delete_book)),
        )
        .await;

        let req = test::TestRequest::get().uri("/books").to_request();
        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), StatusCode::OK);

        let body: Vec<serde_json::Value> = test::read_body_json(resp).await;
        assert_eq!(body.len(), 0);
    }

    #[actix_web::test]
    async fn test_list_books_with_author_filter() {
        let db = create_db();
        let db_data = web::Data::new(Mutex::new(db));

        let app = test::init_service(
            App::new()
                .app_data(db_data)
                .route("/health", web::get().to(health_check))
                .route("/books", web::get().to(list_books))
                .route("/books", web::post().to(create_book))
                .route("/books/{id}", web::get().to(get_book))
                .route("/books/{id}", web::put().to(update_book))
                .route("/books/{id}", web::delete().to(delete_book)),
        )
        .await;

        let payload1 = json!({
            "title": "1984",
            "author": "George Orwell",
            "year": 1949
        });
        test::call_service(
            &app,
            test::TestRequest::post().uri("/books").set_json(payload1).to_request(),
        )
        .await;

        let payload2 = json!({
            "title": "Brave New World",
            "author": "Aldous Huxley",
            "year": 1932
        });
        test::call_service(
            &app,
            test::TestRequest::post().uri("/books").set_json(payload2).to_request(),
        )
        .await;

        let req = test::TestRequest::get()
            .uri("/books?author=Orwell")
            .to_request();
        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), StatusCode::OK);

        let body: Vec<serde_json::Value> = test::read_body_json(resp).await;
        assert_eq!(body.len(), 1);
        assert_eq!(body[0]["author"], "George Orwell");
    }

    #[actix_web::test]
    async fn test_get_book_not_found() {
        let db = create_db();
        let db_data = web::Data::new(Mutex::new(db));

        let app = test::init_service(
            App::new()
                .app_data(db_data)
                .route("/health", web::get().to(health_check))
                .route("/books", web::get().to(list_books))
                .route("/books", web::post().to(create_book))
                .route("/books/{id}", web::get().to(get_book))
                .route("/books/{id}", web::put().to(update_book))
                .route("/books/{id}", web::delete().to(delete_book)),
        )
        .await;

        let req = test::TestRequest::get()
            .uri("/books/nonexistent-id")
            .to_request();
        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), StatusCode::NOT_FOUND);

        let body: serde_json::Value = test::read_body_json(resp).await;
        assert!(body["error"].as_str().unwrap().contains("not found"));
    }

    #[actix_web::test]
    async fn test_update_book() {
        let db = create_db();
        let db_data = web::Data::new(Mutex::new(db));

        let app = test::init_service(
            App::new()
                .app_data(db_data)
                .route("/health", web::get().to(health_check))
                .route("/books", web::get().to(list_books))
                .route("/books", web::post().to(create_book))
                .route("/books/{id}", web::get().to(get_book))
                .route("/books/{id}", web::put().to(update_book))
                .route("/books/{id}", web::delete().to(delete_book)),
        )
        .await;

        let payload = json!({
            "title": "1984",
            "author": "George Orwell",
            "year": 1949
        });
        let create_resp = test::call_service(
            &app,
            test::TestRequest::post().uri("/books").set_json(payload).to_request(),
        )
        .await;
        let created: serde_json::Value = test::read_body_json(create_resp).await;
        let book_id = created["id"].as_str().unwrap();

        let update_payload = json!({
            "title": "1984 - Updated Edition"
        });
        let update_req = test::TestRequest::put()
            .uri(&format!("/books/{}", book_id))
            .set_json(update_payload)
            .to_request();

        let resp = test::call_service(&app, update_req).await;
        assert_eq!(resp.status(), StatusCode::OK);

        let body: serde_json::Value = test::read_body_json(resp).await;
        assert_eq!(body["title"], "1984 - Updated Edition");
        assert_eq!(body["author"], "George Orwell");
    }

    #[actix_web::test]
    async fn test_delete_book() {
        let db = create_db();
        let db_data = web::Data::new(Mutex::new(db));

        let app = test::init_service(
            App::new()
                .app_data(db_data)
                .route("/health", web::get().to(health_check))
                .route("/books", web::get().to(list_books))
                .route("/books", web::post().to(create_book))
                .route("/books/{id}", web::get().to(get_book))
                .route("/books/{id}", web::put().to(update_book))
                .route("/books/{id}", web::delete().to(delete_book)),
        )
        .await;

        let payload = json!({
            "title": "To Kill a Mockingbird",
            "author": "Harper Lee",
            "year": 1960
        });
        let create_resp = test::call_service(
            &app,
            test::TestRequest::post().uri("/books").set_json(payload).to_request(),
        )
        .await;
        let created: serde_json::Value = test::read_body_json(create_resp).await;
        let book_id = created["id"].as_str().unwrap();

        let delete_req = test::TestRequest::delete()
            .uri(&format!("/books/{}", book_id))
            .to_request();

        let resp = test::call_service(&app, delete_req).await;
        assert_eq!(resp.status(), StatusCode::NO_CONTENT);

        // Verify it's gone
        let get_req = test::TestRequest::get()
            .uri(&format!("/books/{}", book_id))
            .to_request();
        let resp = test::call_service(&app, get_req).await;
        assert_eq!(resp.status(), StatusCode::NOT_FOUND);
    }

    #[actix_web::test]
    async fn test_delete_book_not_found() {
        let db = create_db();
        let db_data = web::Data::new(Mutex::new(db));

        let app = test::init_service(
            App::new()
                .app_data(db_data)
                .route("/health", web::get().to(health_check))
                .route("/books", web::get().to(list_books))
                .route("/books", web::post().to(create_book))
                .route("/books/{id}", web::get().to(get_book))
                .route("/books/{id}", web::put().to(update_book))
                .route("/books/{id}", web::delete().to(delete_book)),
        )
        .await;

        let req = test::TestRequest::delete()
            .uri("/books/nonexistent-id")
            .to_request();
        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), StatusCode::NOT_FOUND);
    }
}
