use axum::body::Body;
use axum::http::{Request, StatusCode};
use book_api::test_support::test_app;
use http_body_util::BodyExt;
use tower::ServiceExt;

#[tokio::test]
async fn health_check_returns_ok() {
    let app = test_app();

    let response = app
        .oneshot(
            Request::builder()
                .uri("/health")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);

    let body = response.into_body().collect().await.unwrap().to_bytes();
    let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
    assert_eq!(json["status"], "ok");
}
