mod normalize;
mod data;
mod tools;
mod mcp;

use anyhow::Result;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};

#[tokio::main]
async fn main() -> Result<()> {
    let data_dir = std::env::var("DATA_DIR")
        .unwrap_or_else(|_| "data/kaggle".to_string());

    let db = data::Database::load(&data_dir).await?;
    let db = std::sync::Arc::new(db);

    let stdin = tokio::io::stdin();
    let stdout = tokio::io::stdout();
    let mut reader = BufReader::new(stdin);
    let mut stdout = stdout;
    let mut line = String::new();

    loop {
        line.clear();
        let n = reader.read_line(&mut line).await?;
        if n == 0 {
            break;
        }
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }

        match mcp::handle_request(trimmed, &db) {
            Ok(response) => {
                let mut resp = serde_json::to_string(&response)?;
                resp.push('\n');
                stdout.write_all(resp.as_bytes()).await?;
                stdout.flush().await?;
            }
            Err(e) => {
                let error_resp = serde_json::json!({
                    "jsonrpc": "2.0",
                    "id": null,
                    "error": {
                        "code": -32700,
                        "message": format!("Parse error: {}", e)
                    }
                });
                let mut resp = serde_json::to_string(&error_resp)?;
                resp.push('\n');
                stdout.write_all(resp.as_bytes()).await?;
                stdout.flush().await?;
            }
        }
    }

    Ok(())
}
