use book_api_lib::create_app;
use book_api_lib::AppState;
use std::net::SocketAddr;
use std::sync::Arc;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Create application state
    let app_state = Arc::new(AppState::new().await?);

    // Build the router
    let app = create_app(app_state);

    // Bind to a socket address
    let addr = SocketAddr::from(([127, 0, 0, 1], 3000));
    println!("Server running on http://{}", addr);

    // Start the server
    axum::serve(
        tokio::net::TcpListener::bind(addr).await?,
        app.into_make_service(),
    ).await?;

    Ok(())
}