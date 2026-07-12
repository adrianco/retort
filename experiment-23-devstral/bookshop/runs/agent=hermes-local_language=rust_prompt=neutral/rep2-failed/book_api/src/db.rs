use diesel::prelude::*;
use diesel::sqlite::SqliteConnection;
use dotenvy::dotenv;
use std::env;

pub fn establish_connection() -> SqliteConnection {
    dotenv().ok();
    let database_url = env::var("DATABASE_URL").expect("DATABASE_URL must be set");
    SqliteConnection::establish(&database_url)
        .unwrap_or_else(|_| panic!("Error connecting to database"))
}

pub fn run_migrations(connection: &SqliteConnection) {
    embed_migrations!();
    embedded_migrations::run(connection).unwrap_or_else(|_| panic!("Error running migrations"));
}
