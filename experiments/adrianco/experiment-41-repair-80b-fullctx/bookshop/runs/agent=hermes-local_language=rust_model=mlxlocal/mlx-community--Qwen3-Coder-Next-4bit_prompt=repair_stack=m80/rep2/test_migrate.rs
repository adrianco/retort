fn main() {
    use diesel::prelude::*;
    use diesel::sqlite::SqliteConnection;
    use diesel_migrations::{embed_migrations, EmbeddedMigrations, MigrationHarness};
    
    std::env::set_var("DATABASE_URL", "test_books.db");
    
    let migrations = embed_migrations!("migrations");
    let mut conn = SqliteConnection::establish("test_books.db").unwrap();
    
    println!("Running migrations...");
    let result = conn.run_pending_migrations(migrations);
    println!("Result: {:?}", result);
    
    // Check if table exists
    let tables: Vec<String> = diesel::sql_query("SELECT name FROM sqlite_master WHERE type='table'")
        .load(&mut conn).unwrap();
    println!("Tables: {:?}", tables);
}
