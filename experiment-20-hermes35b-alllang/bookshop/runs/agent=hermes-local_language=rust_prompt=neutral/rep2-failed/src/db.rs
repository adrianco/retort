use sqlx::{FromRow, SqlitePool};
use crate::models::{Book, UpdateBookRequest};

pub async fn init_pool(database_url: &str) -> Result<SqlitePool, sqlx::Error> {
    let pool = SqlitePool::connect(database_url).await?;
    migrate(&pool).await?;
    Ok(pool)
}

async fn migrate(pool: &SqlitePool) -> Result<(), sqlx::Error> {
    sqlx::query(
        "CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        );",
    )
    .execute(pool)
    .await?;
    Ok(())
}

pub async fn create_book(pool: &SqlitePool, id: &str, title: &str, author: &str, year: i32, isbn: &str) -> Result<Book, String> {
    sqlx::query(
        "INSERT INTO books (id, title, author, year, isbn) VALUES (?, ?, ?, ?, ?)",
    )
    .bind(id)
    .bind(title)
    .bind(author)
    .bind(year)
    .bind(isbn)
    .execute(pool)
    .await
    .map_err(|e| format!("Failed to create book: {}", e))?;

    Ok(Book {
        id: id.to_string(),
        title: title.to_string(),
        author: author.to_string(),
        year,
        isbn: isbn.to_string(),
    })
}

pub async fn list_books(pool: &SqlitePool, author: Option<&str>) -> Result<Vec<Book>, String> {
    let books = if let Some(a) = author {
        sqlx::query_as::<_, Book>("SELECT id, title, author, year, isbn FROM books WHERE author = ?")
            .bind(a)
            .fetch_all(pool)
            .await
            .map_err(|e| format!("Failed to list books: {}", e))?
    } else {
        sqlx::query_as::<_, Book>("SELECT id, title, author, year, isbn FROM books")
            .fetch_all(pool)
            .await
            .map_err(|e| format!("Failed to list books: {}", e))?
    };
    Ok(books)
}

pub async fn get_book(pool: &SqlitePool, id: &str) -> Result<Book, String> {
    let book = sqlx::query_as::<_, Book>("SELECT id, title, author, year, isbn FROM books WHERE id = ?")
        .bind(id)
        .fetch_optional(pool)
        .await
        .map_err(|e| format!("Failed to get book: {}", e))?;

    book.ok_or_else(|| format!("Book not found: {}", id))
}

pub async fn update_book(pool: &SqlitePool, id: &str, req: &UpdateBookRequest) -> Result<Book, String> {
    let existing = get_book(pool, id).await?;

    let new_title = req.title.as_deref().unwrap_or(&existing.title);
    let new_author = req.author.as_deref().unwrap_or(&existing.author);
    let new_year = req.year.unwrap_or(existing.year);
    let new_isbn = req.isbn.as_deref().unwrap_or(&existing.isbn);

    sqlx::query(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
    )
    .bind(new_title)
    .bind(new_author)
    .bind(new_year)
    .bind(new_isbn)
    .bind(id)
    .execute(pool)
    .await
    .map_err(|e| format!("Failed to update book: {}", e))?;

    Ok(Book {
        id: id.to_string(),
        title: new_title.to_string(),
        author: new_author.to_string(),
        year: new_year,
        isbn: new_isbn.to_string(),
    })
}

pub async fn delete_book(pool: &SqlitePool, id: &str) -> Result<(), String> {
    let rows = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(id)
        .execute(pool)
        .await
        .map_err(|e| format!("Failed to delete book: {}", e))?;

    if rows.rows_affected() == 0 {
        Err(format!("Book not found: {}", id))
    } else {
        Ok(())
    }
}
