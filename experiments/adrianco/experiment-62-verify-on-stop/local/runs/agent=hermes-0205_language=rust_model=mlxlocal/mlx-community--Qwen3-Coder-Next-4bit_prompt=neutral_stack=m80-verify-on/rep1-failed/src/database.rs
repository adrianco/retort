use sqlx::{sqlite::SqlitePoolOptions, Pool, Sqlite};
use std::sync::Arc;
use tokio::sync::Mutex;

use crate::models::{AppError, Book, BookInput, BookUpdate};

pub type DbPool = Pool<Sqlite>;
pub type AppState = Arc<Mutex<DbPool>>;

pub async fn init_db(db_path: &str) -> Result<DbPool, AppError> {
    let pool = SqlitePoolOptions::new()
        .max_connections(5)
        .connect(db_path)
        .await?;

    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER NOT NULL,
            isbn TEXT NOT NULL UNIQUE
        )
        "#,
    )
    .execute(&pool)
    .await?;

    Ok(pool)
}

pub async fn get_all_books(
    pool: &DbPool,
    author_filter: Option<String>,
) -> Result<Vec<Book>, AppError> {
    let books = if let Some(author) = author_filter {
        sqlx::query_as::<_, Book>(
            r#"
            SELECT id, title, author, year, isbn FROM books
            WHERE author = ?
            "#,
        )
        .bind(author)
        .fetch_all(pool)
        .await?
    } else {
        sqlx::query_as::<_, Book>(
            r#"
            SELECT id, title, author, year, isbn FROM books
            "#,
        )
        .fetch_all(pool)
        .await?
    };
    Ok(books)
}

pub async fn get_book_by_id(pool: &DbPool, id: i64) -> Result<Book, AppError> {
    let book = sqlx::query_as::<_, Book>(
        r#"
        SELECT id, title, author, year, isbn FROM books WHERE id = ?
        "#,
    )
    .bind(id)
    .fetch_one(pool)
    .await?;
    Ok(book)
}

pub async fn create_book(pool: &DbPool, input: BookInput) -> Result<Book, AppError> {
    input.validate()?;

    let book = sqlx::query_as::<_, Book>(
        r#"
        INSERT INTO books (title, author, year, isbn)
        VALUES (?, ?, ?, ?)
        RETURNING id, title, author, year, isbn
        "#,
    )
    .bind(&input.title)
    .bind(&input.author)
    .bind(input.year as i64)
    .bind(&input.isbn)
    .fetch_one(pool)
    .await?;
    Ok(book)
}

pub async fn update_book(
    pool: &DbPool,
    id: i64,
    update: BookUpdate,
) -> Result<Book, AppError> {
    let existing = get_book_by_id(pool, id).await?;
    if existing.id != id {
        return Err(AppError::NotFound(format!("Book with id {} not found", id)));
    }

    let book = sqlx::query_as::<_, Book>(
        r#"
        UPDATE books
        SET title = COALESCE(?, title),
            author = COALESCE(?, author),
            year = COALESCE(?, year),
            isbn = COALESCE(?, isbn)
        WHERE id = ?
        RETURNING id, title, author, year, isbn
        "#,
    )
    .bind(update.title)
    .bind(update.author)
    .bind(update.year.map(|y| y as i64))
    .bind(update.isbn)
    .bind(id)
    .fetch_one(pool)
    .await?;
    Ok(book)
}

pub async fn delete_book(pool: &DbPool, id: i64) -> Result<(), AppError> {
    let rows_affected = sqlx::query(r#"DELETE FROM books WHERE id = ?"#)
        .bind(id)
        .execute(pool)
        .await?
        .rows_affected();
    if rows_affected == 0 {
        return Err(AppError::NotFound(format!("Book with id {} not found", id)));
    }
    Ok(())
}
