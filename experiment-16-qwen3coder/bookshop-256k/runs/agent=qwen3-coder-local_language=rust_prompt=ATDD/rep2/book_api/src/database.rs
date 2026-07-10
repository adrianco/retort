use sqlx::{SqlitePool, Row};
use crate::models::{Book, CreateBook, UpdateBook};

#[derive(Clone)]
pub struct Database {
    pool: SqlitePool,
}

impl Database {
    pub async fn new(database_url: &str) -> Result<Self, sqlx::Error> {
        let pool = SqlitePool::connect(database_url).await?;
        let db = Self { pool };
        db.init().await?;
        Ok(db)
    }

    async fn init(&self) -> Result<(), sqlx::Error> {
        let query = r#"
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER NOT NULL,
                isbn TEXT NOT NULL
            );
        "#;
        sqlx::query(query).execute(&self.pool).await?;
        Ok(())
    }

    pub async fn create_book(&self, book: &CreateBook) -> Result<Book, sqlx::Error> {
        let query = r#"
            INSERT INTO books (title, author, year, isbn)
            VALUES (?1, ?2, ?3, ?4)
            RETURNING id, title, author, year, isbn
        "#;
        
        let book_row = sqlx::query_as::<_, Book>(query)
            .bind(&book.title)
            .bind(&book.author)
            .bind(book.year)
            .bind(&book.isbn)
            .fetch_one(&self.pool)
            .await?;
        
        Ok(book_row)
    }

    pub async fn get_book(&self, id: i32) -> Result<Option<Book>, sqlx::Error> {
        let query = r#"
            SELECT id, title, author, year, isbn
            FROM books
            WHERE id = ?1
        "#;
        
        let book = sqlx::query_as::<_, Book>(query)
            .bind(id)
            .fetch_optional(&self.pool)
            .await?;
        
        Ok(book)
    }

    pub async fn get_books(&self, author: Option<&str>) -> Result<Vec<Book>, sqlx::Error> {
        let query = if let Some(author) = author {
            r#"
                SELECT id, title, author, year, isbn
                FROM books
                WHERE author = ?1
                ORDER BY id
            "#
        } else {
            r#"
                SELECT id, title, author, year, isbn
                FROM books
                ORDER BY id
            "#
        };
        
        let books = if let Some(author) = author {
            sqlx::query_as::<_, Book>(query)
                .bind(author)
                .fetch_all(&self.pool)
                .await?
        } else {
            sqlx::query_as::<_, Book>(query)
                .fetch_all(&self.pool)
                .await?
        };
        
        Ok(books)
    }

    pub async fn update_book(&self, id: i32, book: &UpdateBook) -> Result<Option<Book>, sqlx::Error> {
        // First check if the book exists
        let existing_book = self.get_book(id).await?;
        if existing_book.is_none() {
            return Ok(None);
        }

        // Build the update query dynamically
        let mut query = String::from("UPDATE books SET ");
        let mut updates = Vec::new();

        if let Some(title) = &book.title {
            updates.push(format!("title = '{}'", title.replace("'", "''")));
        }
        if let Some(author) = &book.author {
            updates.push(format!("author = '{}'", author.replace("'", "''")));
        }
        if let Some(year) = book.year {
            updates.push(format!("year = {}", year));
        }
        if let Some(isbn) = &book.isbn {
            updates.push(format!("isbn = '{}'", isbn.replace("'", "''")));
        }

        // If no updates were provided, return early
        if updates.is_empty() {
            return self.get_book(id).await;
        }

        // Join the updates and add WHERE clause
        query.push_str(&updates.join(", "));
        query.push_str(&format!(" WHERE id = {}", id));

        // Execute the query
        sqlx::query(&query).execute(&self.pool).await?;

        // Return the updated book
        self.get_book(id).await
    }

    pub async fn delete_book(&self, id: i32) -> Result<bool, sqlx::Error> {
        let query = r#"
            DELETE FROM books
            WHERE id = ?1
        "#;
        
        let result = sqlx::query(query)
            .bind(id)
            .execute(&self.pool)
            .await?;
        
        Ok(result.rows_affected() > 0)
    }
}