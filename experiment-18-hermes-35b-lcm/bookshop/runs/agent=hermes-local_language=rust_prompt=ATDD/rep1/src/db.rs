use sqlx::{SqlitePool, Result};
use uuid::Uuid;

use crate::models::{Book, CreateBookRequest, UpdateBookRequest};

pub async fn create_pool(database_url: &str) -> Result<SqlitePool> {
    SqlitePool::connect(database_url).await
}

pub async fn init_db(pool: &SqlitePool) -> Result<()> {
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER NOT NULL,
            isbn TEXT NOT NULL
        )
        "#,
    )
    .execute(pool)
    .await?;

    Ok(())
}

pub async fn create_book(pool: &SqlitePool, req: &CreateBookRequest) -> Result<Book> {
    let id = Uuid::new_v4();
    sqlx::query(
        r#"
        INSERT INTO books (id, title, author, year, isbn)
        VALUES (?, ?, ?, ?, ?)
        "#,
    )
    .bind(id.to_string())
    .bind(&req.title.as_ref().unwrap())
    .bind(&req.author.as_ref().unwrap())
    .bind(req.year.unwrap_or(0))
    .bind(req.isbn.as_ref().unwrap())
    .execute(pool)
    .await?;

    Ok(Book {
        id,
        title: req.title.as_ref().unwrap().clone(),
        author: req.author.as_ref().unwrap().clone(),
        year: req.year.unwrap_or(0),
        isbn: req.isbn.as_ref().unwrap().clone(),
    })
}

pub async fn list_books(pool: &SqlitePool, author: Option<&str>) -> Result<Vec<Book>> {
    match author {
        Some(a) => {
            let books = sqlx::query_as::<_, Book>(
                r#"
                SELECT id, title, author, year, isbn FROM books
                WHERE author = ?
                ORDER BY id
                "#,
            )
            .bind(a)
            .fetch_all(pool)
            .await?;
            Ok(books)
        }
        None => {
            let books = sqlx::query_as::<_, Book>(
                r#"
                SELECT id, title, author, year, isbn FROM books
                ORDER BY id
                "#,
            )
            .fetch_all(pool)
            .await?;
            Ok(books)
        }
    }
}

pub async fn get_book(pool: &SqlitePool, id: Uuid) -> Result<Option<Book>> {
    let book = sqlx::query_as::<_, Book>(
        r#"
        SELECT id, title, author, year, isbn FROM books
        WHERE id = ?
        "#,
    )
    .bind(id.to_string())
    .fetch_optional(pool)
    .await?;
    Ok(book)
}

pub async fn update_book(
    pool: &SqlitePool,
    id: Uuid,
    req: &UpdateBookRequest,
) -> Result<Option<Book>> {
    // Get current book first to preserve fields not being updated
    let current = sqlx::query_as::<_, Book>(
        r#"
        SELECT id, title, author, year, isbn FROM books
        WHERE id = ?
        "#,
    )
    .bind(id.to_string())
    .fetch_optional(pool)
    .await?;

    let book = match current {
        Some(b) => {
            let title = req.title.clone().unwrap_or_else(|| b.title.clone());
            let author = req.author.clone().unwrap_or_else(|| b.author.clone());
            let year = req.year.unwrap_or(b.year);
            let isbn = req.isbn.clone().unwrap_or_else(|| b.isbn.clone());

            sqlx::query(
                r#"
                UPDATE books
                SET title = ?, author = ?, year = ?, isbn = ?
                WHERE id = ?
                "#,
            )
            .bind(&title)
            .bind(&author)
            .bind(year)
            .bind(&isbn)
            .bind(id.to_string())
            .execute(pool)
            .await?;

            Some(Book {
                id,
                title,
                author,
                year,
                isbn,
            })
        }
        None => None,
    };

    Ok(book)
}

pub async fn delete_book(pool: &SqlitePool, id: Uuid) -> Result<bool> {
    let rows = sqlx::query(
        r#"
        DELETE FROM books WHERE id = ?
        "#,
    )
    .bind(id.to_string())
    .execute(pool)
    .await?;

    Ok(rows.rows_affected() > 0)
}
