use sqlx::{Row, SqlitePool};

async fn setup_test_db() -> SqlitePool {
    let pool = SqlitePool::connect("sqlite::memory:")
        .await
        .expect("Failed to create test database pool");

    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )
        "#,
    )
    .execute(&pool)
    .await
    .expect("Failed to create books table");

    pool
}

// --- Unit tests for database operations ---

#[tokio::test]
async fn test_create_book_success() {
    let pool = setup_test_db().await;

    let row = sqlx::query("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)")
        .bind("The Rust Programming Language")
        .bind("Steve Klabnik")
        .bind(2018)
        .bind("978-1-7185-0044-0")
        .execute(&pool)
        .await
        .expect("Failed to insert book");

    assert_eq!(row.rows_affected(), 1);

    let book = sqlx::query("SELECT id, title, author, year, isbn FROM books")
        .fetch_one(&pool)
        .await
        .expect("Failed to fetch book");

    assert_eq!(book.get::<String, _>("title"), "The Rust Programming Language");
    assert_eq!(book.get::<String, _>("author"), "Steve Klabnik");
    assert_eq!(book.get::<Option<i32>, _>("year"), Some(2018));
    assert_eq!(
        book.get::<Option<String>, _>("isbn"),
        Some("978-1-7185-0044-0".to_string())
    );
}

#[tokio::test]
async fn test_create_book_minimal() {
    let pool = setup_test_db().await;

    let row = sqlx::query("INSERT INTO books (title, author) VALUES (?, ?)")
        .bind("Minimal Book")
        .bind("Author")
        .execute(&pool)
        .await
        .expect("Failed to insert book");

    assert_eq!(row.rows_affected(), 1);

    let book = sqlx::query("SELECT id, title, author, year, isbn FROM books")
        .fetch_one(&pool)
        .await
        .expect("Failed to fetch book");

    assert_eq!(book.get::<String, _>("title"), "Minimal Book");
    assert_eq!(book.get::<String, _>("author"), "Author");
    assert_eq!(book.get::<Option<i32>, _>("year"), None);
    assert_eq!(book.get::<Option<String>, _>("isbn"), None);
}

#[tokio::test]
async fn test_get_book_by_id() {
    let pool = setup_test_db().await;

    // Insert a book
    sqlx::query("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)")
        .bind("Clean Code")
        .bind("Robert C. Martin")
        .bind(2008)
        .bind("978-0-1323-5088-4")
        .execute(&pool)
        .await
        .expect("Failed to insert");

    // Fetch it
    let book = sqlx::query("SELECT id, title, author, year, isbn FROM books WHERE id = ?")
        .bind(1)
        .fetch_one(&pool)
        .await
        .expect("Failed to fetch");

    assert_eq!(book.get::<i64, _>("id"), 1);
    assert_eq!(book.get::<String, _>("title"), "Clean Code");
    assert_eq!(book.get::<String, _>("author"), "Robert C. Martin");
}

#[tokio::test]
async fn test_get_book_not_found() {
    let pool = setup_test_db().await;

    let result = sqlx::query("SELECT id, title, author, year, isbn FROM books WHERE id = ?")
        .bind(9999)
        .fetch_optional(&pool)
        .await
        .expect("Failed to query");

    assert!(result.is_none());
}

#[tokio::test]
async fn test_list_all_books() {
    let pool = setup_test_db().await;

    // Insert multiple books
    sqlx::query("INSERT INTO books (title, author, year) VALUES (?, ?, ?)")
        .bind("Book One")
        .bind("Author A")
        .bind(2020)
        .execute(&pool)
        .await
        .expect("Failed to insert");

    sqlx::query("INSERT INTO books (title, author, year) VALUES (?, ?, ?)")
        .bind("Book Two")
        .bind("Author B")
        .bind(2021)
        .execute(&pool)
        .await
        .expect("Failed to insert");

    let books = sqlx::query("SELECT id, title, author, year, isbn FROM books")
        .fetch_all(&pool)
        .await
        .expect("Failed to fetch all");

    assert_eq!(books.len(), 2);
}

#[tokio::test]
async fn test_list_books_filter_by_author() {
    let pool = setup_test_db().await;

    // Insert books with different authors
    sqlx::query("INSERT INTO books (title, author, year) VALUES (?, ?, ?)")
        .bind("Rust Book")
        .bind("Alice")
        .bind(2023)
        .execute(&pool)
        .await
        .expect("Failed to insert");

    sqlx::query("INSERT INTO books (title, author, year) VALUES (?, ?, ?)")
        .bind("Go Book")
        .bind("Bob")
        .bind(2022)
        .execute(&pool)
        .await
        .expect("Failed to insert");

    sqlx::query("INSERT INTO books (title, author, year) VALUES (?, ?, ?)")
        .bind("Another Rust Book")
        .bind("Alice")
        .bind(2024)
        .execute(&pool)
        .await
        .expect("Failed to insert");

    // Filter by author
    let books = sqlx::query("SELECT id, title, author, year, isbn FROM books WHERE author = ?")
        .bind("Alice")
        .fetch_all(&pool)
        .await
        .expect("Failed to fetch filtered");

    assert_eq!(books.len(), 2);
    for book in &books {
        assert_eq!(book.get::<String, _>("author"), "Alice");
    }
}

#[tokio::test]
async fn test_update_book() {
    let pool = setup_test_db().await;

    // Insert a book
    sqlx::query("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)")
        .bind("Original Title")
        .bind("Original Author")
        .bind(2020)
        .bind("111-111")
        .execute(&pool)
        .await
        .expect("Failed to insert");

    // Update only the title
    sqlx::query("UPDATE books SET title = ? WHERE id = ?")
        .bind("Updated Title")
        .bind(1)
        .execute(&pool)
        .await
        .expect("Failed to update");

    let book = sqlx::query("SELECT id, title, author, year, isbn FROM books WHERE id = ?")
        .bind(1)
        .fetch_one(&pool)
        .await
        .expect("Failed to fetch");

    assert_eq!(book.get::<String, _>("title"), "Updated Title");
    assert_eq!(book.get::<String, _>("author"), "Original Author"); // unchanged
}

#[tokio::test]
async fn test_update_book_not_found() {
    let pool = setup_test_db().await;

    let result = sqlx::query("UPDATE books SET title = ? WHERE id = ?")
        .bind("New Title")
        .bind(9999)
        .execute(&pool)
        .await
        .expect("Failed to update");

    assert_eq!(result.rows_affected(), 0);
}

#[tokio::test]
async fn test_delete_book() {
    let pool = setup_test_db().await;

    // Insert a book
    sqlx::query("INSERT INTO books (title, author) VALUES (?, ?)")
        .bind("To Delete")
        .bind("Author")
        .execute(&pool)
        .await
        .expect("Failed to insert");

    // Delete it
    let result = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(1)
        .execute(&pool)
        .await
        .expect("Failed to delete");

    assert_eq!(result.rows_affected(), 1);

    // Verify it's gone
    let count = sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM books")
        .fetch_one(&pool)
        .await
        .expect("Failed to count");

    assert_eq!(count, 0);
}

#[tokio::test]
async fn test_delete_book_not_found() {
    let pool = setup_test_db().await;

    let result = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(9999)
        .execute(&pool)
        .await
        .expect("Failed to delete");

    assert_eq!(result.rows_affected(), 0);
}

#[tokio::test]
async fn test_full_crud_workflow() {
    let pool = setup_test_db().await;

    // CREATE
    let row = sqlx::query("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)")
        .bind("Design Patterns")
        .bind("Gang of Four")
        .bind(1994)
        .bind("978-0-2016-3361-0")
        .execute(&pool)
        .await
        .expect("Failed to create");
    let id = row.last_insert_rowid();
    assert_eq!(row.rows_affected(), 1);

    // READ
    let book = sqlx::query("SELECT id, title, author, year, isbn FROM books WHERE id = ?")
        .bind(id)
        .fetch_one(&pool)
        .await
        .expect("Failed to read");
    assert_eq!(book.get::<String, _>("title"), "Design Patterns");

    // UPDATE
    sqlx::query("UPDATE books SET year = ? WHERE id = ?")
        .bind(1995)
        .bind(id)
        .execute(&pool)
        .await
        .expect("Failed to update");

    let book = sqlx::query("SELECT id, title, author, year, isbn FROM books WHERE id = ?")
        .bind(id)
        .fetch_one(&pool)
        .await
        .expect("Failed to read after update");
    assert_eq!(book.get::<Option<i32>, _>("year"), Some(1995));

    // LIST
    let books = sqlx::query("SELECT id, title, author, year, isbn FROM books")
        .fetch_all(&pool)
        .await
        .expect("Failed to list");
    assert_eq!(books.len(), 1);

    // DELETE
    let result = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(id)
        .execute(&pool)
        .await
        .expect("Failed to delete");
    assert_eq!(result.rows_affected(), 1);

    // Verify empty
    let count = sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM books")
        .fetch_one(&pool)
        .await
        .expect("Failed to count");
    assert_eq!(count, 0);
}
