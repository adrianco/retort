use actix_web::{web, App, HttpServer, HttpResponse};

fn health_check() -> HttpResponse {
 HttpResponse::Ok().json("healthy")
}

fn main() -> std::io::Result<()> {
 HttpServer::new(|| {
 App::new()
 .route("/health", web::get().to(health_check))
 })
 .bind("127.0.0.1:8080")?
 .run()
}