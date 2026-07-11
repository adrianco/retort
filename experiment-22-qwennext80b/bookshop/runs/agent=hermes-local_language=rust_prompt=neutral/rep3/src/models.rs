use serde::{Deserialize, Serialize};
use sqlx::{FromRow, Pool, Sqlite};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum BookError {
    #[error("Not found: {0}")]
    NotFound(String),
    #[error("Database error: {0}")]
    Database(#[from] sqlx::Error),
    #[error("Validation error: {0}")]
    Validation(String),
}

impl actix_web::error::ResponseError for BookError {}

#[derive(Debug, Clone, Serialize, FromRow)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: i32,
    pub isbn: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct CreateBookRequest {
    pub title: String,
    pub author: String,
    pub year: i32,
    pub isbn: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct UpdateBookRequest {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

impl CreateBookRequest {
    pub fn validate(&self) -> Result<(), BookError> {
        if self.title.trim().is_empty() {
            return Err(BookError::Validation("title is required".to_string()));
        }
        if self.author.trim().is_empty() {
            return Err(BookError::Validation("author is required".to_string()));
        }
        Ok(())
    }
}

pub async fn init_db(pool: &Pool<Sqlite>) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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

pub async fn create_book(pool: &Pool<Sqlite>, req: CreateBookRequest) -> Result<Book, BookError> {
    req.validate()?;
    
    let book = sqlx::query_as::<_, Book>(
        r#"
        INSERT INTO books (title, author, year, isbn)
        VALUES (?, ?, ?, ?)
        RETURNING id, title, author, year, isbn
        "#,
    )
    .bind(&req.title)
    .bind(&req.author)
    .bind(req.year)
    .bind(&req.isbn)
    .fetch_one(pool)
    .await?;
    
    Ok(book)
}

pub async fn get_books(pool: &Pool<Sqlite>, author: Option<String>) -> Result<Vec<Book>, BookError> {
    let books = if let Some(author) = author {
        sqlx::query_as::<_, Book>(
            r#"SELECT id, title, author, year, isbn FROM books WHERE author = ?"#,
        )
        .bind(author)
        .fetch_all(pool)
        .await?
    } else {
        sqlx::query_as::<_, Book>(
            r#"SELECT id, title, author, year, isbn FROM books"#,
        )
        .fetch_all(pool)
        .await?
    };
    
    Ok(books)
}

pub async fn get_book(pool: &Pool<Sqlite>, id: i64) -> Result<Book, BookError> {
    let book = sqlx::query_as::<_, Book>(
        r#"SELECT id, title, author, year, isbn FROM books WHERE id = ?"#,
    )
    .bind(id)
    .fetch_one(pool)
    .await?;
    
    Ok(book)
}

pub async fn update_book(pool: &Pool<Sqlite>, id: i64, req: UpdateBookRequest) -> Result<Book, BookError> {
    let book = sqlx::query_as::<_, Book>(
        r#"
        UPDATE books
        SET 
            title = COALESCE(?, title),
            author = COALESCE(?, author),
            year = COALESCE(?, year),
            isbn = COALESCE(?, isbn)
        WHERE id = ?
        RETURNING id, title, author, year, isbn
        "#,
    )
    .bind(req.title)
    .bind(req.author)
    .bind(req.year)
    .bind(req.isbn)
    .bind(id)
    .fetch_one(pool)
    .await?;
    
    Ok(book)
}

pub async fn delete_book(pool: &Pool<Sqlite>, id: i64) -> Result<(), BookError> {
    let rows_affected = sqlx::query(r#"DELETE FROM books WHERE id = ?"#)
        .bind(id)
        .execute(pool)
        .await?
        .rows_affected();
    
    if rows_affected == 0 {
        return Err(BookError::NotFound(format!("Book with id {} not found", id)));
    }
    
    Ok(())
}
