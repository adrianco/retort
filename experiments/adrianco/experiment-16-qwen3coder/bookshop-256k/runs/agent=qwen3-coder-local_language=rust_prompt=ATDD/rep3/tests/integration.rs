use serde_json::json;
use std::time::Duration;
use tokio::time::timeout;

// Tests that the basic server functionality works
#[tokio::test]
async fn test_basic_functionality() {
    // Start the server in background
    let handle = tokio::spawn(async {
        let _result = book_api::main().await;
    });
    
    // Give the server time to start
    tokio::time::sleep(Duration::from_millis(1000)).await;
    
    // Test that we can make a request to health endpoint
    let client = reqwest::Client::new();
    let response = client
        .get("http://127.0.0.1:3000/health")
        .send()
        .await
        .expect("Failed to send request");
    
    assert_eq!(response.status(), 200);
    
    // Cancel the server
    handle.abort();
}