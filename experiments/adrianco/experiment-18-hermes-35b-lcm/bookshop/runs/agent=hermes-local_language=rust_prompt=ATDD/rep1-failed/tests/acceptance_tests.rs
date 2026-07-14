
use actix_web::{web, App, test};
use book_api::{init_database, create_app, Book};
use serde_json::json;

// Each test creates its own in-memory pool so tests are independent and share no data.
async fn new_pool() -> sqlx::SqlitePool {
    init_database("sqlite::memory:").await
}

// ============================================================
// Acceptance Test: Health Check Returns 200 With Status OK
// ============================================================

#[actix_web::test]
async fn test_health_check_returns_200_with_status_ok() {
    let pool = new_pool().await;
    let app = test::init_service(create_app(pool)).await;

    let req = test::TestRequest::get().uri("/health").to_request();
    let resp = test::call_service(&app, req).await;

    assert_eq!(resp.status(), 200);
    let body: serde_json::Value = serde_json::from_slice(&resp.into_body().into_bytes().unwrap()).unwrap();
    assert_eq!(body["status"], "ok");
}

// ============================================================
// Acceptance Test: Create Book Returns 201 With Created Book
// ============================================================

#[actix_web::test]
async fn test_create_book_returns_201_with_created_book() {
    let pool = new_pool().await;
    let app = test::init_service(create_app(pool)).await;

    let req = test::TestRequest::post()
        .uri("/books")
        .json(&json!({
            "title": "The Rust Programming Language",
            "author": "Steve Klabnik",
            "year": 2018,
            "isbn": "978-1-7185-0044-1"
        }))
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 201);

    let body: serde_json::Value = serde_json::from_slice(&resp.into_body().into_bytes().unwrap()).unwrap();
    assert_eq!(body["title"], "The Rust Programming Language");
    assert_eq!(body["author"], "Steve Klabnik");
    assert_eq!(body["year"].as_i64(), Some(2018));
    assert_eq!(body["isbn"], "978-1-7185-0044-1");
    assert!(body["id"].as_i64().is_some());
}

// ============================================================
// Acceptance Test: Create Book Without Title Returns 400
// ============================================================

#[actix_web::test]
async fn test_create_book_without_title_returns_400() {
    let pool = new_pool().await;
    let app = test::init_service(create_app(pool)).await;

    let req = test::TestRequest::post()
        .uri("/books")
        .json(&json!({
            "author": "John Doe",
            "year": 2020
        }))
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 400);

    let body: serde_json::Value = serde_json::from_slice(&resp.into_body().into_bytes().unwrap()).unwrap();
    assert_eq!(body["error"], "Title is required");
}

// ============================================================
// Acceptance Test: Create Book Without Author Returns 400
// ============================================================

#[actix_web::test]
async fn test_create_book_without_author_returns_400() {
    let pool = new_pool().await;
    let app = test::init_service(create_app(pool)).await;

    let req = test::TestRequest::post()
        .uri("/books")
        .json(&json!({
            "title": "Some Book"
        }))
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 400);

    let body: serde_json::Value = serde_json::from_slice(&resp.into_body().into_bytes().unwrap()).unwrap();
    assert_eq!(body["error"], "Author is required");
}

// ============================================================
// Acceptance Test: List All Books Returns Empty List When No Books
// ============================================================

#[actix_web::test]
async fn test_list_books_returns_empty_list_when_no_books() {
    let pool = new_pool().await;
    let app = test::init_service(create_app(pool)).await;

    let req = test::TestRequest::get().uri("/books").to_request();
    let resp = test::call_service(&app, req).await;

    assert_eq!(resp.status(), 200);
    let body: Vec<serde_json::Value> = serde_json::from_slice(&resp.into_body().into_bytes().unwrap()).unwrap();
    assert!(body.is_empty());
}

// ============================================================
// Acceptance Test: List All Books Returns All Stored Books
// ============================================================

#[actix_web::test]
async fn test_list_books_returns_all_books() {
    let pool = new_pool().await;

    let _: Book = sqlx::query_as!(
        Book,
        r#"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING id, title, author, year, isbn"#,
        "Book A", "Author One", 2020, "isbn-a"
    ).fetch_one(&pool).await.unwrap();

    let _: Book = sqlx::query_as!(
        Book,
        r#"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING id, title, author, year, isbn"#,
        "Book B", "Author Two", 2021, "isbn-b"
    ).fetch_one(&pool).await.unwrap();

    let app = test::init_service(create_app(pool)).await;

    let req = test::TestRequest::get().uri("/books").to_request();
    let resp = test::call_service(&app, req).await;

    assert_eq!(resp.status(), 200);
    let body: Vec<serde_json::Value> = serde_json::from_slice(&resp.into_body().into_bytes().unwrap()).unwrap();
    assert_eq!(body.len(), 2);
    assert_eq!(body[0]["title"], "Book A");
    assert_eq!(body[1]["title"], "Book B");
}

// ============================================================
// Acceptance Test: Filter Books By Author
// ============================================================

#[actix_web::test]
async fn test_list_books_filters_by_author() {
    let pool = new_pool().await;

    let _: Book = sqlx::query_as!(
        Book,
        r#"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING id, title, author, year, isbn"#,
        "Rust Book", "Steve K", 2018, "isbn-r1"
    ).fetch_one(&pool).await.unwrap();

    let _: Book = sqlx::query_as!(
        Book,
        r#"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING id, title, author, year, isbn"#,
        "Python Book", "Jane Doe", 2020, "isbn-p1"
    ).fetch_one(&pool).await.unwrap();

    let _: Book = sqlx::query_as!(
        Book,
        r#"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING id, title, author, year, isbn"#,
        "Rust Guide", "Steve K", 2022, "isbn-r2"
    ).fetch_one(&pool).await.unwrap();

    let app = test::init_service(create_app(pool)).await;

    let req = test::TestRequest::get().uri("/books?author=Steve+K").to_request();
    let resp = test::call_service(&app, req).await;

    assert_eq!(resp.status(), 200);
    let body: Vec<serde_json::Value> = serde_json::from_slice(&resp.into_body().into_bytes().unwrap()).unwrap();
    assert_eq!(body.len(), 2);
    for b in &body {
        assert_eq!(b["author"], "Steve K");
    }
}

// ============================================================
// Acceptance Test: Get Book By ID Returns The Book
// ============================================================

#[actix_web::test]
async fn test_get_book_returns_book_by_id() {
    let pool = new_pool().await;

    let book: Book = sqlx::query_as!(
        Book,
        r#"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING id, title, author, year, isbn"#,
        "Dune", "Frank Herbert", 1965, "978-0-441-17271-9"
    ).fetch_one(&pool).await.unwrap();

    let app = test::init_service(create_app(pool)).await;

    let req = test::TestRequest::get()
        .uri(&format!("/books/{}", book.id))
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);

    let body: serde_json::Value = serde_json::from_slice(&resp.into_body().into_bytes().unwrap()).unwrap();
    assert_eq!(body["id"], book.id as i64);
    assert_eq!(body["title"], "Dune");
    assert_eq!(body["author"], "Frank Herbert");
    assert_eq!(body["year"].as_i64(), Some(1965));
}

// ============================================================
// Acceptance Test: Get Nonexistent Book Returns 404
// ============================================================

#[actix_web::test]
async fn test_get_book_returns_404_for_nonexistent_id() {
    let pool = new_pool().await;
    let app = test::init_service(create_app(pool)).await;

    let req = test::TestRequest::get()
        .uri("/books/999")
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 404);

    let body: serde_json::Value = serde_json::from_slice(&resp.into_body().into_bytes().unwrap()).unwrap();
    assert_eq!(body["error"], "Book not found");
}

// ============================================================
// Acceptance Test: Update Book Returns Updated Book
// ============================================================

#[actix_web::test]
async fn test_update_book_returns_updated_book() {
    let pool = new_pool().await;

    let book: Book = sqlx::query_as!(
        Book,
        r#"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING id, title, author, year, isbn"#,
        "Old Title", "Old Author", 2020, "isbn-old"
    ).fetch_one(&pool).await.unwrap();

    let app = test::init_service(create_app(pool)).await;

    let req = test::TestRequest::put()
        .uri(&format!("/books/{}", book.id))
        .json(&json!({
            "title": "New Title",
            "author": "New Author",
            "year": 2023,
            "isbn": "isbn-new"
        }))
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);

    let body: serde_json::Value = serde_json::from_slice(&resp.into_body().into_bytes().unwrap()).unwrap();
    assert_eq!(body["title"], "New Title");
    assert_eq!(body["author"], "New Author");
    assert_eq!(body["year"].as_i64(), Some(2023));
    assert_eq!(body["isbn"], "isbn-new");
}

// ============================================================
// Acceptance Test: Partial Update Preserves Other Fields
// ============================================================

#[actix_web::test]
async fn test_update_book_partial_update_preserves_other_fields() {
    let pool = new_pool().await;

    let book: Book = sqlx::query_as!(
        Book,
        r#"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING id, title, author, year, isbn"#,
        "Original", "Author One", 2020, "isbn-orig"
    ).fetch_one(&pool).await.unwrap();

    let app = test::init_service(create_app(pool)).await;

    // Only update title
    let req = test::TestRequest::put()
        .uri(&format!("/books/{}", book.id))
        .json(&json!({
            "title": "Only Title Changed"
        }))
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);

    let body: serde_json::Value = serde_json::from_slice(&resp.into_body().into_bytes().unwrap()).unwrap();
    assert_eq!(body["title"], "Only Title Changed");
    assert_eq!(body["author"], "Author One");
    assert_eq!(body["year"].as_i64(), Some(2020));
    assert_eq!(body["isbn"], "isbn-orig");
}

// ============================================================
// Acceptance Test: Update Nonexistent Book Returns 404
// ============================================================

#[actix_web::test]
async fn test_update_book_returns_404_for_nonexistent_id() {
    let pool = new_pool().await;
    let app = test::init_service(create_app(pool)).await;

    let req = test::TestRequest::put()
        .uri("/books/999")
        .json(&json!({
            "title": "New Title",
            "author": "New Author"
        }))
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 404);

    let body: serde_json::Value = serde_json::from_slice(&resp.into_body().into_bytes().unwrap()).unwrap();
    assert_eq!(body["error"], "Book not found");
}

// ============================================================
// Acceptance Test: Delete Book Returns 204
// ============================================================

#[actix_web::test]
async fn test_delete_book_returns_204() {
    let pool = new_pool().await;

    let book: Book = sqlx::query_as!(
        Book,
        r#"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING id, title, author, year, isbn"#,
        "To Delete", "Author", 2022, "isbn-del"
    ).fetch_one(&pool).await.unwrap();

    let app = test::init_service(create_app(pool)).await;

    let req = test::TestRequest::delete()
        .uri(&format!("/books/{}", book.id))
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 204);
}

// ============================================================
// Acceptance Test: Delete Nonexistent Book Returns 404
// ============================================================

#[actix_web::test]
async fn test_delete_book_returns_404_for_nonexistent_id() {
    let pool = new_pool().await;
    let app = test::init_service(create_app(pool)).await;

    let req = test::TestRequest::delete()
        .uri("/books/999")
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 404);

    let body: serde_json::Value = serde_json::from_slice(&resp.into_body().into_bytes().unwrap()).unwrap();
    assert_eq!(body["error"], "Book not found");
}

// ============================================================
// Acceptance Test: Deleted Book Is Removed From The List
// ============================================================

#[actix_web::test]
async fn test_delete_book_removes_book_from_list() {
    let pool = new_pool().await;

    let book: Book = sqlx::query_as!(
        Book,
        r#"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING id, title, author, year, isbn"#,
        "To Remove", "Author", 2023, "isbn-remove"
    ).fetch_one(&pool).await.unwrap();

    let app = test::init_service(create_app(pool)).await;

    // Delete first
    let del_req = test::TestRequest::delete()
        .uri(&format!("/books/{}", book.id))
        .to_request();
    let del_resp = test::call_service(&app, del_req).await;
    assert_eq!(del_resp.status(), 204);

    // Verify the list is now empty
    let list_req = test::TestRequest::get().uri("/books").to_request();
    let list_resp = test::call_service(&app, list_req).await;
    assert_eq!(list_resp.status(), 200);

    let body: Vec<serde_json::Value> = serde_json::from_slice(&list_resp.into_body().into_bytes().unwrap()).unwrap();
    assert_eq!(body.len(), 0);
}

// ============================================================
// Acceptance Test: Update Book With Empty Title Returns 400
// ============================================================

#[actix_web::test]
async fn test_update_book_with_empty_title_returns_400() {
    let pool = new_pool().await;

    let book: Book = sqlx::query_as!(
        Book,
        r#"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING id, title, author, year, isbn"#,
        "Original", "Author", 2020, "isbn-1"
    ).fetch_one(&pool).await.unwrap();

    let app = test::init_service(create_app(pool)).await;

    let req = test::TestRequest::put()
        .uri(&format!("/books/{}", book.id))
        .json(&json!({
            "title": "",
            "author": "New Author"
        }))
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 400);
}

// ============================================================
// Acceptance Test: Create Book Without Optional Fields Succeeds
// ============================================================

#[actix_web::test]
async fn test_create_book_without_optional_fields_succeeds() {
    let pool = new_pool().await;
    let app = test::init_service(create_app(pool)).await;

    let req = test::TestRequest::post()
        .uri("/books")
        .json(&json!({
            "title": "Minimal Book",
            "author": "Author Only"
        }))
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 201);

    let body: serde_json::Value = serde_json::from_slice(&resp.into_body().into_bytes().unwrap()).unwrap();
    assert_eq!(body["title"], "Minimal Book");
    assert_eq!(body["author"], "Author Only");
    assert!(body["year"].is_null());
    assert!(body["isbn"].is_null());
}
