use book_api::start_server;

#[actix_web::main]
async fn main() -> Result<(), book_api::AppError> {
    start_server("127.0.0.1", 8080).await?;
    Ok(())
}
