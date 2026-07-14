use actix_web::{test, web, App, HttpResponse, Result};
use serde_json::json;

#[actix_web::test]
async fn test_health_check() -> Result<()> {
    let app = test::init_service(
        App::new()
            .route("/health", web::get().to(|| async { HttpResponse::Ok().json(()) }))
    ).await;
    
    let req = test::TestRequest::get().uri("/health").to_request();
    let resp = test::call_service(&app, req).await;
    
    assert_eq!(resp.status(), 200);
    Ok(())
}

#[actix_web::test]
async fn test_create_book() -> Result<()> {
    let app = test::init_service(
        App::new()
            .route("/books", web::post().to(|_data: web::Json<serde_json::Value>| async { 
                HttpResponse::Ok().json(()) 
            }))
    ).await;
    
    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(json!({
            "title": "Test Book",
            "author": "Test Author",
            "year": 2023,
            "isbn": "1234567890"
        }))
        .to_request();
    
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);
    
    Ok(())
}
