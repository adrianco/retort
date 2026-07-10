use serde::{Deserialize, Serialize};
use sqlx::{SqlitePool, Row};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Book {
    pub id: Option<i64>,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

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
                year INTEGER,
                isbn TEXT
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
            
        let id = row.get(0);
        Ok(Book {
            id: Some(id),
            title: book.title.clone(),
            author: book.author.clone(),
            year: book.year,
            isbn: book.isbn.clone(),
        })
    }

    pub async fn get_book(&self, id: i64) -> Result<Option<Book>, sqlx::Error> {
        let query = r#"SELECT id, title, author, year, isbn FROM books WHERE id = ?"#;
        let row = sqlx::query(query)
            .bind(id)
            .fetch_optional(&self.pool)
            .await?;
            
        match row {
            Some(row) => {
                let book = Book {
                    id: Some(row.get(0)),
                    title: row.get(1),
                    author: row.get(2),
                    year: row.get(3),
                    isbn: row.get(4),
                };
                Ok(Some(book))
            }
            None => Ok(None),
        }
    }

    pub async fn list_books(&self, author_filter: Option<&str>) -> Result<Vec<Book>, sqlx::Error> {
        let query = if let Some(_author) = author_filter {
            r#"SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY title"#.to_string()
        } else {
            r#"SELECT id, title, author, year, isbn FROM books ORDER BY title"#.to_string()
        };
        
        let rows = sqlx::query(&query);
        
        let rows = if let Some(author) = author_filter {
            rows.bind(author)
        } else {
            rows
        };
        
        let results = rows.fetch_all(&self.pool).await?;
        let mut books: Vec<Book> = Vec::new();
        
        for row in results {
            let book = Book {
                id: Some(row.get(0)),
                title: row.get(1),
                author: row.get(2),
                year: row.get(3),
                isbn: row.get(4),
            };
            books.push(book);
        }
        
        Ok(books)
    }

    pub async fn update_book(&self, id: i64, book: &Book) -> Result<Option<Book>, sqlx::Error> {
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
            .await?
            .rows_affected();
            
        if rows_affected == 0 {
            Ok(None)
        } else {
            Ok(Some(Book {
                id: Some(id),
                title: book.title.clone(),
                author: book.author.clone(),
                year: book.year,
                isbn: book.isbn.clone(),
            }))
        }
    }

    pub async fn delete_book(&self, id: i64) -> Result<bool, sqlx::Error> {
        let query = r#"DELETE FROM books WHERE id = ?"#;
        let rows_affected = sqlx::query(query)
            .bind(id)
            .execute(&self.pool)
            .await?
            .rows_affected();
            
        Ok(rows_affected > 0)
    }
}