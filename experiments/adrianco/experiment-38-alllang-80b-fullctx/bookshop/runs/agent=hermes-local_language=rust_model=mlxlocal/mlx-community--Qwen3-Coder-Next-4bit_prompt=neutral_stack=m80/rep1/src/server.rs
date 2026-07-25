use crate::db;
use crate::routes;
use crate::db::AppState;

use actix_web::{web, App, HttpServer, HttpResponse, Result};
use serde::{Deserialize, Serialize};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum AppError {
    #[error("Database error: {0}")]
    Database(#[from] sqlx::Error),
    #[error("Validation error: {0}")]
    Validation(String),
    #[error("Not found")]
    NotFound,
    #[error("Server error: {0}")]
    Server(#[from] std::io::Error),
}

impl actix_web::ResponseError for AppError {
    fn status_code(&self) -> actix_web::http::StatusCode {
        match self {
            AppError::Database(_) => actix_web::http::StatusCode::INTERNAL_SERVER_ERROR,
            AppError::Validation(_) => actix_web::http::StatusCode::BAD_REQUEST,
            AppError::NotFound => actix_web::http::StatusCode::NOT_FOUND,
            AppError::Server(_) => actix_web::http::StatusCode::INTERNAL_SERVER_ERROR,
        }
    }

    fn error_response(&self) -> HttpResponse {
        HttpResponse::build(self.status_code()).json(serde_json::json!({
            "error": self.to_string()
        }))
    }
}

#[derive(Debug, Serialize, Deserialize)]
pub struct HealthResponse {
    pub status: String,
    pub timestamp: String,
}

pub async fn health() -> Result<HttpResponse, AppError> {
    Ok(HttpResponse::Ok().json(HealthResponse {
        status: "ok".to_string(),
        timestamp: chrono::Utc::now().to_rfc3339(),
    }))
}

pub async fn start_server(host: &str, port: u16) -> Result<(), AppError> {
    // Initialize database
    let pool = db::init_db().await?;
    
    let state = std::sync::Arc::new(AppState {
        pool: pool.clone(),
    });

    println!("Starting server on http://{}:{}", host, port);

    let server = HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(state.clone()))
            .configure(routes::configure_routes)
    })
    .bind(format!("{}:{}", host, port))?;

    server.run().await?;
    Ok(())
}
