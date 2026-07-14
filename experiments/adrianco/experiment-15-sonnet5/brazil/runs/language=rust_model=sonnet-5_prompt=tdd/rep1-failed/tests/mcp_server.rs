use std::path::Path;
use std::sync::Arc;

use brazilian_soccer_mcp::server::SoccerServer;
use brazilian_soccer_mcp::store::Store;
use rmcp::model::{CallToolRequestParams, ClientRequest, Request};
use rmcp::{ClientHandler, ServiceExt};

#[derive(Default, Clone)]
struct TestClient;

impl ClientHandler for TestClient {}

fn test_store() -> Arc<Store> {
    let dir = Path::new(env!("CARGO_MANIFEST_DIR")).join("data/kaggle");
    Arc::new(Store::load_from_dir(&dir).unwrap())
}

#[tokio::test]
async fn lists_all_expected_tools() -> anyhow::Result<()> {
    let server = SoccerServer::new(test_store());
    let (server_transport, client_transport) = tokio::io::duplex(4096);
    let server_handle = tokio::spawn(async move {
        let service = server.serve(server_transport).await?;
        service.waiting().await?;
        anyhow::Ok(())
    });

    let client = TestClient::default().serve(client_transport).await?;
    let tools = client.list_all_tools().await?;
    let names: Vec<&str> = tools.iter().map(|t| t.name.as_ref()).collect();

    for expected in [
        "search_matches",
        "head_to_head",
        "team_record",
        "standings",
        "biggest_wins",
        "match_stats",
        "players_by_name",
        "players_by_nationality",
        "players_by_club",
        "top_rated_players",
    ] {
        assert!(names.contains(&expected), "missing tool: {expected}");
    }

    client.cancel().await?;
    let _ = server_handle.await;
    Ok(())
}

#[tokio::test]
async fn head_to_head_tool_returns_expected_summary() -> anyhow::Result<()> {
    let server = SoccerServer::new(test_store());
    let (server_transport, client_transport) = tokio::io::duplex(4096);
    let server_handle = tokio::spawn(async move {
        let service = server.serve(server_transport).await?;
        service.waiting().await?;
        anyhow::Ok(())
    });

    let client = TestClient::default().serve(client_transport).await?;
    let params = CallToolRequestParams::new("head_to_head").with_arguments(
        serde_json::json!({ "team_a": "Flamengo", "team_b": "Fluminense" })
            .as_object()
            .unwrap()
            .clone(),
    );
    let response = client
        .send_request(ClientRequest::CallToolRequest(Request::new(params)))
        .await?;
    let rmcp::model::ServerResult::CallToolResult(result) = response else {
        panic!("expected call tool result, got {response:?}");
    };
    let text = result
        .content
        .iter()
        .filter_map(|c| c.as_text().map(|t| t.text.clone()))
        .collect::<Vec<_>>()
        .join("\n");
    assert!(text.contains("Head-to-head:"));
    assert!(text.contains("Flamengo"));
    assert!(text.contains("Fluminense"));

    client.cancel().await?;
    let _ = server_handle.await;
    Ok(())
}
