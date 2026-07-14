use book_api::{AppState, migrate, get_pool, configure_routes};
use actix_web::{web, App, HttpServer};
use serde::Serialize;

#[derive(Serialize)]
pub struct HealthResponse {
    pub status: String,
    pub timestamp: u64,
}

async fn health() -> actix_web::HttpResponse {
    actix_web::HttpResponse::Ok().json(HealthResponse {
        status: "ok".to_string(),
        timestamp: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs(),
    })
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init_from_env(env_logger::Env::new().default_filter_or("info"));

    let pool = get_pool().await;

    // Run migrations
    migrate(&pool).await.expect("Failed to run migrations");

    log::info!("Starting server on http://127.0.0.1:8080");

    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(AppState {
                pool: pool.clone(),
            }))
            .route("/health", web::get().to(health))
            .configure(configure_routes)
    })
    .bind("127.0.0.1:8080")?
    .run()
    .await
}
