use crate::{AppError, Book, CreateBookRequest, UpdateBookRequest};
use sqlx::SqlitePool;

#[derive(Clone)]
pub struct BookRepository {
    pool: SqlitePool,
}

impl BookRepository {
    pub async fn new(database_url: &str) -> Result<Self, AppError> {
        let pool = SqlitePool::connect(database_url).await?;
        Self::create_tables(&pool).await?;
        Ok(Self { pool })
    }

    async fn create_tables(pool: &SqlitePool) -> Result<(), AppError> {
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
        .execute(pool)
        .await?;
        Ok(())
    }

    pub async fn create_book(&self, req: &CreateBookRequest) -> Result<Book, AppError> {
        let book = sqlx::query_as::<_, Book>(
            r#"
            INSERT INTO books (title, author, year, isbn)
            VALUES (?, ?, ?, ?)
            RETURNING id, title, author, year, isbn
            "#,
        )
        .bind(&req.title)
        .bind(&req.author)
        .bind(req.year as i64)
        .bind(&req.isbn)
        .fetch_one(&self.pool)
        .await?;
        Ok(book)
    }

    pub async fn get_books(&self, author: Option<String>) -> Result<Vec<Book>, AppError> {
        let books = if let Some(author) = author {
            sqlx::query_as::<_, Book>(
                r#"SELECT id, title, author, year, isbn FROM books WHERE author = ?"#,
            )
            .bind(author)
            .fetch_all(&self.pool)
            .await?
        } else {
            sqlx::query_as::<_, Book>(r#"SELECT id, title, author, year, isbn FROM books"#)
                .fetch_all(&self.pool)
                .await?
        };
        Ok(books)
    }

    pub async fn get_book_by_id(&self, id: i64) -> Result<Book, AppError> {
        let book = sqlx::query_as::<_, Book>(
            r#"SELECT id, title, author, year, isbn FROM books WHERE id = ?"#,
        )
        .bind(id)
        .fetch_one(&self.pool)
        .await?;
        Ok(book)
    }

    pub async fn update_book(&self, id: i64, req: &UpdateBookRequest) -> Result<Book, AppError> {
        let book = sqlx::query_as::<_, Book>(
            r#"
            UPDATE books
            SET 
                title = COALESCE(NULLIF(?, ''), title),
                author = COALESCE(NULLIF(?, ''), author),
                year = COALESCE(?, year),
                isbn = COALESCE(NULLIF(?, ''), isbn)
            WHERE id = ?
            RETURNING id, title, author, year, isbn
            "#,
        )
        .bind(req.title.as_ref().map(|s| s.as_str()))
        .bind(req.author.as_ref().map(|s| s.as_str()))
        .bind(req.year.map(|y| y as i64))
        .bind(req.isbn.as_ref().map(|s| s.as_str()))
        .bind(id)
        .fetch_one(&self.pool)
        .await?;
        Ok(book)
    }

    pub async fn delete_book(&self, id: i64) -> Result<(), AppError> {
        let rows_affected = sqlx::query(r#"DELETE FROM books WHERE id = ?"#)
            .bind(id)
            .execute(&self.pool)
            .await?
            .rows_affected();
        if rows_affected == 0 {
            return Err(AppError::NotFound);
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sqlx::Sqlite;

    async fn setup_test_db() -> SqlitePool {
        SqlitePool::connect(":memory:").await.unwrap()
    }

    #[tokio::test]
    async fn test_create_tables() {
        let pool = setup_test_db().await;
        BookRepository::create_tables(&pool).await.unwrap();
        
        let count: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='books'")
            .fetch_one(&pool)
            .await
            .unwrap();
        assert_eq!(count, 1);
    }

    #[tokio::test]
    async fn test_create_book() {
        let pool = setup_test_db().await;
        BookRepository::create_tables(&pool).await.unwrap();
        let repo = BookRepository { pool };
        
        let req = CreateBookRequest {
            title: "Test Book".to_string(),
            author: "Test Author".to_string(),
            year: 2024,
            isbn: "1234567890".to_string(),
        };
        
        let book = repo.create_book(&req).await.unwrap();
        assert_eq!(book.title, "Test Book");
        assert_eq!(book.author, "Test Author");
        assert_eq!(book.year, 2024);
        assert_eq!(book.isbn, "1234567890");
        assert!(book.id > 0);
    }

    #[tokio::test]
    async fn test_get_books() {
        let pool = setup_test_db().await;
        BookRepository::create_tables(&pool).await.unwrap();
        let repo = BookRepository { pool };
        
        let req1 = CreateBookRequest {
            title: "Book 1".to_string(),
            author: "Author A".to_string(),
            year: 2020,
            isbn: "1111111111".to_string(),
        };
        let req2 = CreateBookRequest {
            title: "Book 2".to_string(),
            author: "Author B".to_string(),
            year: 2021,
            isbn: "2222222222".to_string(),
        };
        
        repo.create_book(&req1).await.unwrap();
        repo.create_book(&req2).await.unwrap();
        
        let all_books = repo.get_books(None).await.unwrap();
        assert_eq!(all_books.len(), 2);
        
        let filtered = repo.get_books(Some("Author A".to_string())).await.unwrap();
        assert_eq!(filtered.len(), 1);
        assert_eq!(filtered[0].author, "Author A");
    }

    #[tokio::test]
    async fn test_update_book() {
        let pool = setup_test_db().await;
        BookRepository::create_tables(&pool).await.unwrap();
        let repo = BookRepository { pool };
        
        let req = CreateBookRequest {
            title: "Original Title".to_string(),
            author: "Original Author".to_string(),
            year: 2020,
            isbn: "1111111111".to_string(),
        };
        let book = repo.create_book(&req).await.unwrap();
        
        let update_req = UpdateBookRequest {
            title: Some("Updated Title".to_string()),
            author: None,
            year: Some(2021),
            isbn: None,
        };
        
        let updated_book = repo.update_book(book.id, &update_req).await.unwrap();
        assert_eq!(updated_book.title, "Updated Title");
        assert_eq!(updated_book.author, "Original Author");
        assert_eq!(updated_book.year, 2021);
    }

    #[tokio::test]
    async fn test_delete_book() {
        let pool = setup_test_db().await;
        BookRepository::create_tables(&pool).await.unwrap();
        let repo = BookRepository { pool };
        
        let req = CreateBookRequest {
            title: "To Delete".to_string(),
            author: "Author".to_string(),
            year: 2020,
            isbn: "1111111111".to_string(),
        };
        let book = repo.create_book(&req).await.unwrap();
        
        repo.delete_book(book.id).await.unwrap();
        
        let all_books = repo.get_books(None).await.unwrap();
        assert_eq!(all_books.len(), 0);
    }
}
