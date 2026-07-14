mod api;
mod db;
mod models;

use actix_web::{web, App, HttpServer};
use tracing_subscriber::fmt;

#[actix_web::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    fmt().init();

    let pool = db::init_db_pool().await?;
    models::init_db(&pool).await?;

    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(pool.clone()))
            .configure(api::configure)
    })
    .bind("127.0.0.1:8080")?
    .run()
    .await?;

    Ok(())
}
