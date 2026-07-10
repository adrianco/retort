use book_api::{create_router, init_db};
use axum::{body::Body, http::StatusCode};
use http::Request;
use http_body_util::BodyExt;
use serde_json::json;
use sqlx::SqlitePool;
use tokio::runtime::Handle;
use tower::ServiceExt;

fn make_pool() -> SqlitePool {
    Handle::current().block_on(async {
        let pool = SqlitePool::connect("sqlite::memory:").await.unwrap();
        init_db(&pool).await;
        pool
    })
}

// ─── Tests ───────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_health_check() {
    let pool = make_pool();
    let app = create_router(pool.clone());
    let req = Request::builder()
        .uri("/health")
        .body(Body::empty())
        .unwrap();

    let resp = app.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::OK);

    let body_bytes = resp.into_body().collect().await.unwrap().to_bytes();
    assert_eq!(&*body_bytes, b"OK");
}

#[tokio::test]
async fn test_create_book() {
    let pool = make_pool();
    let app = create_router(pool.clone());
    let body = json!({
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
        "isbn": "978-0743273565"
    });
    let req = Request::builder()
        .method("POST")
        .uri("/books")
        .header("content-type", "application/json")
        .body(Body::from(serde_json::to_string(&body).unwrap()))
        .unwrap();

    let resp = app.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::CREATED);

    let body_value: serde_json::Value = resp
        .into_body()
        .collect()
        .await
        .unwrap()
        .to_bytes()
        .as_ref()
        .into();
    assert_eq!(body_value["title"], "The Great Gatsby");
    assert_eq!(body_value["author"], "F. Scott Fitzgerald");
    assert_eq!(body_value["year"], 1925);
    assert!(body_value.get("id").is_some());
}

#[tokio::test]
async fn test_create_book_missing_title() {
    let pool = make_pool();
    let app = create_router(pool.clone());
    let body = json!({
        "author": "Unknown Author",
        "year": 2000
    });
    let req = Request::builder()
        .method("POST")
        .uri("/books")
        .header("content-type", "application/json")
        .body(Body::from(serde_json::to_string(&body).unwrap()))
        .unwrap();

    let resp = app.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);

    let body_value: serde_json::Value = resp
        .into_body()
        .collect()
        .await
        .unwrap()
        .to_bytes()
        .as_ref()
        .into();
    assert_eq!(body_value["message"], "title is required");
}

#[tokio::test]
async fn test_create_book_missing_author() {
    let pool = make_pool();
    let app = create_router(pool.clone());
    let body = json!({
        "title": "Some Book"
    });
    let req = Request::builder()
        .method("POST")
        .uri("/books")
        .header("content-type", "application/json")
        .body(Body::from(serde_json::to_string(&body).unwrap()))
        .unwrap();

    let resp = app.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);

    let body_value: serde_json::Value = resp
        .into_body()
        .collect()
        .await
        .unwrap()
        .to_bytes()
        .as_ref()
        .into();
    assert_eq!(body_value["message"], "author is required");
}

#[tokio::test]
async fn test_create_book_without_optional_fields() {
    let pool = make_pool();
    let app = create_router(pool.clone());
    let body = json!({
        "title": "Simple Book",
        "author": "Test Author"
    });
    let req = Request::builder()
        .method("POST")
        .uri("/books")
        .header("content-type", "application/json")
        .body(Body::from(serde_json::to_string(&body).unwrap()))
        .unwrap();

    let resp = app.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::CREATED);

    let body_value: serde_json::Value = resp
        .into_body()
        .collect()
        .await
        .unwrap()
        .to_bytes()
        .as_ref()
        .into();
    assert_eq!(body_value["title"], "Simple Book");
    assert_eq!(body_value["author"], "Test Author");
    assert_eq!(body_value["year"], serde_json::Value::Null);
    assert_eq!(body_value["isbn"], serde_json::Value::Null);
}

#[tokio::test]
async fn test_list_books() {
    let pool = make_pool();
    // Insert test data
    sqlx::query("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)")
        .bind("The Great Gatsby")
        .bind("F. Scott Fitzgerald")
        .bind(1925)
        .bind("978-0743273565")
        .execute(&pool)
        .await
        .unwrap();

    sqlx::query("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)")
        .bind("The Catcher in the Rye")
        .bind("J.D. Salinger")
        .bind(1951)
        .bind("978-0316769488")
        .execute(&pool)
        .await
        .unwrap();

    let app = create_router(pool.clone());
    let req = Request::builder()
        .uri("/books")
        .body(Body::empty())
        .unwrap();

    let resp = app.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::OK);

    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    let body_value: Vec<serde_json::Value> = serde_json::from_slice(&bytes).unwrap();
    assert_eq!(body_value.len(), 2);
}

#[tokio::test]
async fn test_filter_by_author() {
    let pool = make_pool();
    sqlx::query("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)")
        .bind("1984")
        .bind("George Orwell")
        .bind(1949)
        .bind("978-0451524935")
        .execute(&pool)
        .await
        .unwrap();

    sqlx::query("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)")
        .bind("Animal Farm")
        .bind("George Orwell")
        .bind(1945)
        .bind("978-0451526342")
        .execute(&pool)
        .await
        .unwrap();

    sqlx::query("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)")
        .bind("The Great Gatsby")
        .bind("F. Scott Fitzgerald")
        .bind(1925)
        .bind("978-0743273565")
        .execute(&pool)
        .await
        .unwrap();

    let app = create_router(pool.clone());
    let req = Request::builder()
        .uri("/books?author=George%20Orwell")
        .body(Body::empty())
        .unwrap();

    let resp = app.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::OK);

    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    let body_value: Vec<serde_json::Value> = serde_json::from_slice(&bytes).unwrap();
    assert_eq!(body_value.len(), 2);
    for book in &body_value {
        assert_eq!(book["author"], "George Orwell");
    }
}

#[tokio::test]
async fn test_get_book() {
    let pool = make_pool();
    sqlx::query("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)")
        .bind("1984")
        .bind("George Orwell")
        .bind(1949)
        .bind("978-0451524935")
        .execute(&pool)
        .await
        .unwrap();

    let app = create_router(pool.clone());
    let req = Request::builder()
        .uri("/books/1")
        .body(Body::empty())
        .unwrap();

    let resp = app.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::OK);

    let body_value: serde_json::Value = resp
        .into_body()
        .collect()
        .await
        .unwrap()
        .to_bytes()
        .as_ref()
        .into();
    assert_eq!(body_value["title"], "1984");
    assert_eq!(body_value["author"], "George Orwell");
    assert_eq!(body_value["year"], 1949);
}

#[tokio::test]
async fn test_get_nonexistent_book() {
    let pool = make_pool();
    let app = create_router(pool.clone());
    let req = Request::builder()
        .uri("/books/999")
        .body(Body::empty())
        .unwrap();

    let resp = app.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_update_book() {
    let pool = make_pool();
    sqlx::query("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)")
        .bind("Dune")
        .bind("Frank Herbert")
        .bind(1965)
        .bind("978-0441172719")
        .execute(&pool)
        .await
        .unwrap();

    let app = create_router(pool.clone());
    let body = json!({
        "title": "Dune (Modified)",
        "year": 1965,
        "isbn": "978-0441172719"
    });
    let req = Request::builder()
        .method("PUT")
        .uri("/books/1")
        .header("content-type", "application/json")
        .body(Body::from(serde_json::to_string(&body).unwrap()))
        .unwrap();

    let resp = app.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::OK);

    let body_value: serde_json::Value = resp
        .into_body()
        .collect()
        .await
        .unwrap()
        .to_bytes()
        .as_ref()
        .into();
    assert_eq!(body_value["title"], "Dune (Modified)");
    assert_eq!(body_value["author"], "Frank Herbert");
}

#[tokio::test]
async fn test_update_nonexistent_book() {
    let pool = make_pool();
    let app = create_router(pool.clone());
    let body = json!({
        "title": "Ghost Book"
    });
    let req = Request::builder()
        .method("PUT")
        .uri("/books/999")
        .header("content-type", "application/json")
        .body(Body::from(serde_json::to_string(&body).unwrap()))
        .unwrap();

    let resp = app.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_delete_book() {
    let pool = make_pool();
    sqlx::query("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)")
        .bind("Brave New World")
        .bind("Aldous Huxley")
        .bind(1932)
        .bind("978-0060850524")
        .execute(&pool)
        .await
        .unwrap();

    let app = create_router(pool.clone());
    let req = Request::builder()
        .method("DELETE")
        .uri("/books/1")
        .body(Body::empty())
        .unwrap();

    let resp = app.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::NO_CONTENT);

    // Verify book is deleted
    let app2 = create_router(pool);
    let req = Request::builder()
        .uri("/books/1")
        .body(Body::empty())
        .unwrap();
    let resp = app2.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_delete_nonexistent_book() {
    let pool = make_pool();
    let app = create_router(pool.clone());
    let req = Request::builder()
        .method("DELETE")
        .uri("/books/999")
        .body(Body::empty())
        .unwrap();

    let resp = app.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}
