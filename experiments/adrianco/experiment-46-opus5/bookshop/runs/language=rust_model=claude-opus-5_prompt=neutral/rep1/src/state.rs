use std::path::Path;
use std::sync::{Arc, Mutex};

use rusqlite::Connection;

use crate::db;
use crate::error::ApiError;

/// Shared handle to the SQLite connection.
///
/// SQLite is fast enough locally that a single connection behind a mutex is
/// plenty; the work runs on a blocking thread so it never stalls the async
/// runtime.
#[derive(Clone)]
pub struct AppState {
    conn: Arc<Mutex<Connection>>,
}

impl AppState {
    /// Open (or create) the database file at `path` and apply the schema.
    pub fn open(path: impl AsRef<Path>) -> Result<Self, ApiError> {
        let conn = Connection::open(path)?;
        Self::from_connection(conn)
    }

    /// A private in-memory database, used by the tests.
    pub fn in_memory() -> Result<Self, ApiError> {
        let conn = Connection::open_in_memory()?;
        Self::from_connection(conn)
    }

    fn from_connection(conn: Connection) -> Result<Self, ApiError> {
        db::init_schema(&conn)?;
        Ok(Self {
            conn: Arc::new(Mutex::new(conn)),
        })
    }

    /// Run a blocking database closure off the async runtime's worker threads.
    pub async fn with_conn<T, F>(&self, f: F) -> Result<T, ApiError>
    where
        F: FnOnce(&Connection) -> Result<T, ApiError> + Send + 'static,
        T: Send + 'static,
    {
        let conn = Arc::clone(&self.conn);
        tokio::task::spawn_blocking(move || {
            // A poisoned mutex means a previous query panicked mid-statement;
            // the connection itself is still usable, so carry on.
            let guard = conn.lock().unwrap_or_else(|e| e.into_inner());
            f(&guard)
        })
        .await
        .map_err(|e| ApiError::Internal(format!("database task failed: {e}")))?
    }
}
