use diesel::prelude::*;
use diesel::sqlite::SqliteConnection;
use diesel_migrations::{embed_migrations, EmbeddedMigrations, MigrationHarness};
use std::error::Error;

pub const MIGRATIONS: EmbeddedMigrations = embed_migrations!("migrations");

pub fn get_db_connection() -> SqliteConnection {
    let database_url = std::env::var("DATABASE_URL").unwrap_or_else(|_| "books.db".to_string());
    SqliteConnection::establish(&database_url)
        .unwrap_or_else(|e| panic!("Error connecting to database: {}", e))
}

pub fn run_migrations() -> Result<(), Box<dyn Error>> {
    let mut conn = get_db_connection();
    println!("Running migrations on database: {}", std::env::var("DATABASE_URL").unwrap_or_else(|_| "books.db".to_string()));
    let result = conn.run_pending_migrations(MIGRATIONS);
    println!("Migration result: {:?}", result);
    result.map_err(|e| format!("Migration error: {}", e))?;
    Ok(())
}

#[derive(Clone)]
pub struct AppState {
    pub database_url: String,
}

impl AppState {
    pub fn new() -> Self {
        let database_url = std::env::var("DATABASE_URL").unwrap_or_else(|_| "books.db".to_string());
        Self { database_url }
    }

    pub fn get_connection(&self) -> SqliteConnection {
        SqliteConnection::establish(&self.database_url)
            .expect("Failed to create database connection")
    }
}
