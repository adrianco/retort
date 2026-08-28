use axum::body::Body;
use axum::http::{Request, StatusCode};
use super::create_router;
use super::create_test_pool;
use super::BookCreate;
use super::BookResponse;
use super::BookUpdate;
use tower::util::ServiceExt;

async fn init_test_db(pool: &sqlx::SqlitePool) {
    sqlx::query(
        "CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )",
    )
    .execute(pool)
    .await
    .unwrap();
}

async fn make_app() -> axum::Router {
    let pool = create_test_pool().await;
    init_test_db(&pool).await;
    create_router(pool)
}

async fn send_request(app: axum::Router, req: Request<Body>) -> axum::http::Response<Body> {
    app.oneshot(req).await.unwrap()
}

async fn get_body(resp: axum::http::Response<Body>) -> Vec<u8> {
    axum::body::to_bytes(resp.into_body(), usize::MAX)
        .await
        .unwrap()
        .to_vec()
}

async fn json_value(resp: axum::http::Response<Body>) -> serde_json::Value {
    let body = get_body(resp).await;
    serde_json::from_slice(&body).unwrap()
}

async fn json_typed<T: serde::de::DeserializeOwned>(resp: axum::http::Response<Body>) -> T {
    let body = get_body(resp).await;
    serde_json::from_slice(&body).unwrap()
}

#[tokio::test]
async fn test_health_check() {
    let app = make_app().await;

    let req = Request::builder()
        .method("GET")
        .uri("/health")
        .body(Body::empty())
        .unwrap();

    let resp = send_request(app, req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let body = json_value(resp).await;
    assert_eq!(body["status"], "ok");
}

#[tokio::test]
async fn test_create_book_success() {
    let app = make_app().await;

    let book = BookCreate {
        title: "The Rust Programming Language".to_string(),
        author: "Steve Klabnik".to_string(),
        year: Some(2019),
        isbn: Some("978-1-7185-0044-4".to_string()),
    };

    let req = Request::builder()
        .method("POST")
        .uri("/books")
        .header("content-type", "application/json")
        .body(Body::from(serde_json::to_string(&book).unwrap()))
        .unwrap();

    let resp = send_request(app, req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let body: BookResponse = json_typed(resp).await;
    assert_eq!(body.title, "The Rust Programming Language");
    assert_eq!(body.author, "Steve Klabnik");
    assert_eq!(body.year, Some(2019));
    assert_eq!(body.isbn, Some("978-1-7185-0044-4".to_string()));
    assert!(!body.id.is_empty());
}

#[tokio::test]
async fn test_create_book_missing_title() {
    let app = make_app().await;

    let book = BookCreate {
        title: "".to_string(),
        author: "Some Author".to_string(),
        year: None,
        isbn: None,
    };

    let req = Request::builder()
        .method("POST")
        .uri("/books")
        .header("content-type", "application/json")
        .body(Body::from(serde_json::to_string(&book).unwrap()))
        .unwrap();

    let resp = send_request(app, req).await;
    assert_eq!(resp.status(), StatusCode::UNPROCESSABLE_ENTITY);

    let body = json_value(resp).await;
    assert!(body["error"].as_str().unwrap().contains("title"));
}

#[tokio::test]
async fn test_create_book_missing_author() {
    let app = make_app().await;

    let book = BookCreate {
        title: "My Book".to_string(),
        author: "".to_string(),
        year: None,
        isbn: None,
    };

    let req = Request::builder()
        .method("POST")
        .uri("/books")
        .header("content-type", "application/json")
        .body(Body::from(serde_json::to_string(&book).unwrap()))
        .unwrap();

    let resp = send_request(app, req).await;
    assert_eq!(resp.status(), StatusCode::UNPROCESSABLE_ENTITY);

    let body = json_value(resp).await;
    assert!(body["error"].as_str().unwrap().contains("author"));
}

#[tokio::test]
async fn test_list_books() {
    let app = make_app().await;

    let books = vec![
        BookCreate {
            title: "Book A".to_string(),
            author: "Author One".to_string(),
            year: Some(2020),
            isbn: None,
        },
        BookCreate {
            title: "Book B".to_string(),
            author: "Author One".to_string(),
            year: Some(2021),
            isbn: None,
        },
        BookCreate {
            title: "Book C".to_string(),
            author: "Author Two".to_string(),
            year: Some(2022),
            isbn: None,
        },
    ];

    for book in &books {
        let req = Request::builder()
            .method("POST")
            .uri("/books")
            .header("content-type", "application/json")
            .body(Body::from(serde_json::to_string(book).unwrap()))
            .unwrap();
        send_request(app.clone(), req).await;
    }

    let req = Request::builder()
        .method("GET")
        .uri("/books")
        .body(Body::empty())
        .unwrap();

    let resp = send_request(app, req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let body: Vec<BookResponse> = json_typed(resp).await;
    assert_eq!(body.len(), 3);
}

#[tokio::test]
async fn test_list_books_filter_by_author() {
    let app = make_app().await;

    let book1 = BookCreate {
        title: "Book A".to_string(),
        author: "Author One".to_string(),
        year: Some(2020),
        isbn: None,
    };
    let book2 = BookCreate {
        title: "Book B".to_string(),
        author: "Author Two".to_string(),
        year: Some(2021),
        isbn: None,
    };

    for book in &[book1, book2] {
        let req = Request::builder()
            .method("POST")
            .uri("/books")
            .header("content-type", "application/json")
            .body(Body::from(serde_json::to_string(book).unwrap()))
            .unwrap();
        send_request(app.clone(), req).await;
    }

    let req = Request::builder()
        .method("GET")
        .uri("/books?author=Author+One")
        .body(Body::empty())
        .unwrap();

    let resp = send_request(app, req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let body: Vec<BookResponse> = json_typed(resp).await;
    assert_eq!(body.len(), 1);
    assert_eq!(body[0].author, "Author One");
}

#[tokio::test]
async fn test_get_book() {
    let app = make_app().await;

    let book = BookCreate {
        title: "Test Book".to_string(),
        author: "Test Author".to_string(),
        year: Some(2023),
        isbn: Some("123-456".to_string()),
    };

    let create_req = Request::builder()
        .method("POST")
        .uri("/books")
        .header("content-type", "application/json")
        .body(Body::from(serde_json::to_string(&book).unwrap()))
        .unwrap();

    let create_resp = send_request(app.clone(), create_req).await;
    let created: BookResponse = json_typed(create_resp).await;

    let req = Request::builder()
        .method("GET")
        .uri(format!("/books/{}", created.id))
        .body(Body::empty())
        .unwrap();

    let resp = send_request(app, req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let body: BookResponse = json_typed(resp).await;
    assert_eq!(body.id, created.id);
    assert_eq!(body.title, "Test Book");
    assert_eq!(body.year, Some(2023));
}

#[tokio::test]
async fn test_get_book_not_found() {
    let app = make_app().await;

    let req = Request::builder()
        .method("GET")
        .uri("/books/nonexistent-id")
        .body(Body::empty())
        .unwrap();

    let resp = send_request(app, req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);

    let body = json_value(resp).await;
    assert!(body["error"].as_str().unwrap().contains("not found"));
}

#[tokio::test]
async fn test_update_book() {
    let app = make_app().await;

    let book = BookCreate {
        title: "Original Title".to_string(),
        author: "Original Author".to_string(),
        year: Some(2020),
        isbn: Some("old-isbn".to_string()),
    };

    let create_req = Request::builder()
        .method("POST")
        .uri("/books")
        .header("content-type", "application/json")
        .body(Body::from(serde_json::to_string(&book).unwrap()))
        .unwrap();

    let create_resp = send_request(app.clone(), create_req).await;
    let created: BookResponse = json_typed(create_resp).await;

    let update = BookUpdate {
        title: Some("Updated Title".to_string()),
        author: None,
        year: Some(Some(2024)),
        isbn: Some(Some("new-isbn".to_string())),
    };

    let req = Request::builder()
        .method("PUT")
        .uri(format!("/books/{}", created.id))
        .header("content-type", "application/json")
        .body(Body::from(serde_json::to_string(&update).unwrap()))
        .unwrap();

    let resp = send_request(app, req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let body: BookResponse = json_typed(resp).await;
    assert_eq!(body.title, "Updated Title");
    assert_eq!(body.author, "Original Author");
    assert_eq!(body.year, Some(2024));
    assert_eq!(body.isbn, Some("new-isbn".to_string()));
}

#[tokio::test]
async fn test_update_book_not_found() {
    let app = make_app().await;

    let update = BookUpdate {
        title: Some("New Title".to_string()),
        author: None,
        year: None,
        isbn: None,
    };

    let req = Request::builder()
        .method("PUT")
        .uri("/books/nonexistent-id")
        .header("content-type", "application/json")
        .body(Body::from(serde_json::to_string(&update).unwrap()))
        .unwrap();

    let resp = send_request(app, req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_delete_book() {
    let app = make_app().await;

    let book = BookCreate {
        title: "To Delete".to_string(),
        author: "Author".to_string(),
        year: None,
        isbn: None,
    };

    let create_req = Request::builder()
        .method("POST")
        .uri("/books")
        .header("content-type", "application/json")
        .body(Body::from(serde_json::to_string(&book).unwrap()))
        .unwrap();

    let create_resp = send_request(app.clone(), create_req).await;
    let created: BookResponse = json_typed(create_resp).await;

    let req = Request::builder()
        .method("DELETE")
        .uri(format!("/books/{}", created.id))
        .body(Body::empty())
        .unwrap();

    let resp = send_request(app.clone(), req).await;
    assert_eq!(resp.status(), StatusCode::NO_CONTENT);

    // Verify it's gone
    let req = Request::builder()
        .method("GET")
        .uri(format!("/books/{}", created.id))
        .body(Body::empty())
        .unwrap();

    let resp = send_request(app, req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_delete_book_not_found() {
    let app = make_app().await;

    let req = Request::builder()
        .method("DELETE")
        .uri("/books/nonexistent-id")
        .body(Body::empty())
        .unwrap();

    let resp = send_request(app, req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_full_crud_workflow() {
    let app = make_app().await;

    // CREATE
    let book = BookCreate {
        title: "Rust in Action".to_string(),
        author: "Justin Demello".to_string(),
        year: Some(2020),
        isbn: Some("978-1-6172-9438-7".to_string()),
    };

    let create_req = Request::builder()
        .method("POST")
        .uri("/books")
        .header("content-type", "application/json")
        .body(Body::from(serde_json::to_string(&book).unwrap()))
        .unwrap();

    let create_resp = send_request(app.clone(), create_req).await;
    assert_eq!(create_resp.status(), StatusCode::OK);
    let created: BookResponse = json_typed(create_resp).await;

    // READ
    let req = Request::builder()
        .method("GET")
        .uri(format!("/books/{}", created.id))
        .body(Body::empty())
        .unwrap();

    let resp = send_request(app.clone(), req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let read: BookResponse = json_typed(resp).await;
    assert_eq!(read.id, created.id);
    assert_eq!(read.title, "Rust in Action");

    // UPDATE
    let update = BookUpdate {
        title: Some("Rust in Action (2nd Ed)".to_string()),
        author: None,
        year: Some(Some(2024)),
        isbn: None,
    };

    let req = Request::builder()
        .method("PUT")
        .uri(format!("/books/{}", created.id))
        .header("content-type", "application/json")
        .body(Body::from(serde_json::to_string(&update).unwrap()))
        .unwrap();

    let resp = send_request(app.clone(), req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let updated: BookResponse = json_typed(resp).await;
    assert_eq!(updated.title, "Rust in Action (2nd Ed)");
    assert_eq!(updated.year, Some(2024));

    // DELETE
    let req = Request::builder()
        .method("DELETE")
        .uri(format!("/books/{}", created.id))
        .body(Body::empty())
        .unwrap();

    let resp = send_request(app.clone(), req).await;
    assert_eq!(resp.status(), StatusCode::NO_CONTENT);

    // Verify deletion
    let req = Request::builder()
        .method("GET")
        .uri(format!("/books/{}", created.id))
        .body(Body::empty())
        .unwrap();

    let resp = send_request(app, req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}
