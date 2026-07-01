use axum::body::Body;
use axum::http::{Request, StatusCode};
use book_api::test_support::test_app;
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

async fn body_json(response: axum::response::Response) -> Value {
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    serde_json::from_slice(&bytes).unwrap()
}

async fn create_book(app: &axum::Router, payload: Value) -> Value {
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(payload.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::CREATED);
    body_json(response).await
}

#[tokio::test]
async fn create_book_returns_201_with_created_book() {
    let app = test_app();

    let payload = json!({
        "title": "The Pragmatic Programmer",
        "author": "David Thomas",
        "year": 1999,
        "isbn": "978-0135957059"
    });

    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(payload.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::CREATED);

    let book = body_json(response).await;
    assert_eq!(book["title"], "The Pragmatic Programmer");
    assert_eq!(book["author"], "David Thomas");
    assert_eq!(book["year"], 1999);
    assert_eq!(book["isbn"], "978-0135957059");
    assert!(book["id"].is_i64());
}

#[tokio::test]
async fn create_book_without_title_returns_400() {
    let app = test_app();

    let payload = json!({
        "author": "David Thomas",
        "year": 1999,
        "isbn": "978-0135957059"
    });

    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(payload.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn list_books_returns_all_created_books() {
    let app = test_app();

    create_book(
        &app,
        json!({"title": "Book One", "author": "Author A", "year": 2001, "isbn": "111"}),
    )
    .await;
    create_book(
        &app,
        json!({"title": "Book Two", "author": "Author B", "year": 2002, "isbn": "222"}),
    )
    .await;

    let response = app
        .oneshot(
            Request::builder()
                .uri("/books")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
    let books = body_json(response).await;
    assert_eq!(books.as_array().unwrap().len(), 2);
}

#[tokio::test]
async fn list_books_filters_by_author() {
    let app = test_app();

    create_book(
        &app,
        json!({"title": "Book One", "author": "Author A", "year": 2001, "isbn": "111"}),
    )
    .await;
    create_book(
        &app,
        json!({"title": "Book Two", "author": "Author B", "year": 2002, "isbn": "222"}),
    )
    .await;

    let response = app
        .oneshot(
            Request::builder()
                .uri("/books?author=Author%20A")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
    let books = body_json(response).await;
    let books = books.as_array().unwrap();
    assert_eq!(books.len(), 1);
    assert_eq!(books[0]["author"], "Author A");
}

#[tokio::test]
async fn get_book_by_id_returns_book() {
    let app = test_app();

    let created = create_book(
        &app,
        json!({"title": "Book One", "author": "Author A", "year": 2001, "isbn": "111"}),
    )
    .await;
    let id = created["id"].as_i64().unwrap();

    let response = app
        .oneshot(
            Request::builder()
                .uri(format!("/books/{id}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
    let book = body_json(response).await;
    assert_eq!(book["id"], id);
    assert_eq!(book["title"], "Book One");
}

#[tokio::test]
async fn get_book_by_missing_id_returns_404() {
    let app = test_app();

    let response = app
        .oneshot(
            Request::builder()
                .uri("/books/9999")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn update_book_returns_updated_book() {
    let app = test_app();

    let created = create_book(
        &app,
        json!({"title": "Book One", "author": "Author A", "year": 2001, "isbn": "111"}),
    )
    .await;
    let id = created["id"].as_i64().unwrap();

    let update_payload = json!({
        "title": "Book One Revised",
        "author": "Author A",
        "year": 2005,
        "isbn": "111-revised"
    });

    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("PUT")
                .uri(format!("/books/{id}"))
                .header("content-type", "application/json")
                .body(Body::from(update_payload.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
    let updated = body_json(response).await;
    assert_eq!(updated["id"], id);
    assert_eq!(updated["title"], "Book One Revised");
    assert_eq!(updated["year"], 2005);
    assert_eq!(updated["isbn"], "111-revised");

    let get_response = app
        .oneshot(
            Request::builder()
                .uri(format!("/books/{id}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    let fetched = body_json(get_response).await;
    assert_eq!(fetched["title"], "Book One Revised");
}

#[tokio::test]
async fn update_missing_book_returns_404() {
    let app = test_app();

    let update_payload = json!({
        "title": "Nonexistent",
        "author": "Nobody",
        "year": 2000,
        "isbn": "000"
    });

    let response = app
        .oneshot(
            Request::builder()
                .method("PUT")
                .uri("/books/9999")
                .header("content-type", "application/json")
                .body(Body::from(update_payload.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn update_book_with_invalid_data_returns_400() {
    let app = test_app();

    let created = create_book(
        &app,
        json!({"title": "Book One", "author": "Author A", "year": 2001, "isbn": "111"}),
    )
    .await;
    let id = created["id"].as_i64().unwrap();

    let update_payload = json!({
        "title": "",
        "author": "Author A",
        "year": 2005,
        "isbn": "111"
    });

    let response = app
        .oneshot(
            Request::builder()
                .method("PUT")
                .uri(format!("/books/{id}"))
                .header("content-type", "application/json")
                .body(Body::from(update_payload.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn delete_book_removes_it() {
    let app = test_app();

    let created = create_book(
        &app,
        json!({"title": "Book One", "author": "Author A", "year": 2001, "isbn": "111"}),
    )
    .await;
    let id = created["id"].as_i64().unwrap();

    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("DELETE")
                .uri(format!("/books/{id}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::NO_CONTENT);

    let get_response = app
        .oneshot(
            Request::builder()
                .uri(format!("/books/{id}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(get_response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn delete_missing_book_returns_404() {
    let app = test_app();

    let response = app
        .oneshot(
            Request::builder()
                .method("DELETE")
                .uri("/books/9999")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn create_book_without_author_returns_400() {
    let app = test_app();

    let payload = json!({
        "title": "The Pragmatic Programmer",
        "year": 1999,
        "isbn": "978-0135957059"
    });

    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(payload.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}
