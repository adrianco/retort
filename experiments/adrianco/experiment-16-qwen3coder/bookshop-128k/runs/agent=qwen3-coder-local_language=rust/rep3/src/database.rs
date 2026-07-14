use sqlx::{SqlitePool, Row};
use crate::models::Book;

pub struct Database {
    pool: SqlitePool,
}

impl Database {
    pub async fn new(database_url: &str) -> Result<Self, sqlx::Error> {
        let pool = SqlitePool::connect(database_url).await?;
        let db = Database { pool };
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

    pub async fn create_book(&self, book: &Book) -> Result<Book, sqlx::Error> {
        let query = r#"
            INSERT INTO books (title, author, year, isbn)
            VALUES (?, ?, ?, ?)
            RETURNING id
        "#;
        
        let row = sqlx::query(query)
            .bind(&book.title)
            .bind(&book.author)
            .bind(book.year)
            .bind(&book.isbn)
            .fetch_one(&self.pool)
            .await?;
            
        let id: i32 = row.get(0);
        
        Ok(Book {
            id: Some(id),
            title: book.title.clone(),
            author: book.author.clone(),
            year: book.year,
            isbn: book.isbn.clone(),
        })
    }

    pub async fn get_book(&self, id: i32) -> Result<Option<Book>, sqlx::Error> {
        let query = r#"SELECT * FROM books WHERE id = ?"#;
        let row = sqlx::query(query)
            .bind(id)
            .fetch_optional(&self.pool)
            .await?;
            
        match row {
            Some(row) => {
                let book = Book::from(row);
                Ok(Some(book))
            }
            None => Ok(None),
        }
    }

    pub async fn get_books(&self, author: Option<&str>) -> Result<Vec<Book>, sqlx::Error> {
        let query = if let Some(author) = author {
            r#"SELECT * FROM books WHERE author = ? ORDER BY id"#.to_string()
        } else {
            r#"SELECT * FROM books ORDER BY id"#.to_string()
        };
        
        let rows = sqlx::query(&query)
            .bind(author)
            .fetch_all(&self.pool)
            .await?;
            
        let mut books = Vec::new();
        for row in rows {
            let book = Book::from(row);
            books.push(book);
        }
        
        Ok(books)
    }

    pub async fn update_book(&self, id: i32, book: &Book) -> Result<Option<Book>, sqlx::Error> {
        let query = r#"
            UPDATE books 
            SET title = ?, author = ?, year = ?, isbn = ?
            WHERE id = ?
        "#;
        
        let rows_affected = sqlx::query(query)
            .bind(&book.title)
            .bind(&book.author)
            .bind(book.year)
            .bind(&book.isbn)
            .bind(id)
            .execute(&self.pool)
            .await?;
            
        if rows_affected.rows_affected() == 0 {
            Ok(None)
        } else {
            let query = r#"SELECT * FROM books WHERE id = ?"#;
            let row = sqlx::query(query)
                .bind(id)
                .fetch_one(&self.pool)
                .await?;
                
            let updated_book = Book::from(row);
            Ok(Some(updated_book))
        }
    }

    pub async fn delete_book(&self, id: i32) -> Result<bool, sqlx::Error> {
        let query = r#"DELETE FROM books WHERE id = ?"#;
        let rows_affected = sqlx::query(query)
            .bind(id)
            .execute(&self.pool)
            .await?;
            
        Ok(rows_affected.rows_affected() > 0)
    }
}