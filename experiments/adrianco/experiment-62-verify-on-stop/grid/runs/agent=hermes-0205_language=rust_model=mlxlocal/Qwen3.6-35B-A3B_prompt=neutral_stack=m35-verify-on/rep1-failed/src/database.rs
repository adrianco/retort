use chrono::Utc;
use crate::models::{Book, CreateBookRequest, UpdateBookRequest};
use rusqlite::Connection;

pub fn create_book(conn: &Connection, req: &CreateBookRequest) -> Result<Book, String> {
    // Validation: title and author are required
    let title = req.title.as_ref().ok_or("title is required".to_string())?;
    let author = req.author.as_ref().ok_or("author is required".to_string())?;

    if title.trim().is_empty() {
        return Err("title cannot be empty".to_string());
    }
    if author.trim().is_empty() {
        return Err("author cannot be empty".to_string());
    }

    let id = uuid::Uuid::new_v4().to_string();
    let now = Utc::now().to_rfc3339();

    conn.execute(
        "INSERT INTO books (id, title, author, year, isbn, created_at, updated_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
        rusqlite::params![
            id,
            title,
            author,
            req.year,
            &req.isbn,
            &now,
            &now,
        ],
    ).map_err(|e| format!("Failed to insert book: {}", e))?;

    get_book_by_id(conn, &id)
}

pub fn list_books(conn: &Connection, author_filter: Option<&str>) -> Result<Vec<Book>, String> {
    let books = if let Some(author) = author_filter {
        let mut stmt = conn.prepare(
            "SELECT id, title, author, year, isbn, created_at, updated_at
             FROM books WHERE author LIKE ?1"
        ).map_err(|e| format!("Failed to prepare statement: {}", e))?;

        let mut rows = stmt.query(rusqlite::params![format!("%{}%", author)]).map_err(|e| format!("Failed to execute query: {}", e))?;
        let mut books = Vec::new();
        while let Some(row) = rows.next().map_err(|e| format!("Failed to fetch row: {}", e))? {
            books.push(book_from_row(row));
        }
        books
    } else {
        let mut stmt = conn.prepare(
            "SELECT id, title, author, year, isbn, created_at, updated_at
             FROM books ORDER BY created_at DESC"
        ).map_err(|e| format!("Failed to prepare statement: {}", e))?;

        let mut rows = stmt.query(rusqlite::params![]).map_err(|e| format!("Failed to execute query: {}", e))?;
        let mut books = Vec::new();
        while let Some(row) = rows.next().map_err(|e| format!("Failed to fetch row: {}", e))? {
            books.push(book_from_row(row));
        }
        books
    };

    Ok(books)
}

pub fn get_book_by_id(conn: &Connection, id: &str) -> Result<Book, String> {
    let mut stmt = conn.prepare(
        "SELECT id, title, author, year, isbn, created_at, updated_at
         FROM books WHERE id = ?1"
    ).map_err(|e| format!("Failed to prepare statement: {}", e))?;

    let mut rows = stmt.query(rusqlite::params![id]).map_err(|e| format!("Failed to execute query: {}", e))?;

    let row = rows.next().map_err(|e| format!("Failed to fetch row: {}", e))?;
    match row {
        Some(row) => Ok(book_from_row(row)),
        None => Err(format!("Book with id '{}' not found", id)),
    }
}

pub fn update_book(conn: &Connection, id: &str, req: &UpdateBookRequest) -> Result<Book, String> {
    // First check the book exists
    let existing = get_book_by_id(conn, id)?;

    let new_title = req.title.as_ref().map(|s| {
        if s.trim().is_empty() {
            Err("title cannot be empty".to_string())
        } else {
            Ok(s.clone())
        }
    }).transpose()?;

    let new_author = req.author.as_ref().map(|s| {
        if s.trim().is_empty() {
            Err("author cannot be empty".to_string())
        } else {
            Ok(s.clone())
        }
    }).transpose()?;

    let title = new_title.unwrap_or_else(|| existing.title.clone());
    let author = new_author.unwrap_or_else(|| existing.author.clone());
    let year = req.year.or(existing.year);
    let isbn = req.isbn.clone().or(existing.isbn);
    let now = Utc::now().to_rfc3339();

    conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4, updated_at = ?5
         WHERE id = ?6",
        rusqlite::params![title, author, year, &isbn, &now, id],
    ).map_err(|e| format!("Failed to update book: {}", e))?;

    get_book_by_id(conn, id)
}

pub fn delete_book(conn: &Connection, id: &str) -> Result<(), String> {
    let mut stmt = conn.prepare("DELETE FROM books WHERE id = ?1").map_err(|e| format!("Failed to prepare statement: {}", e))?;
    let rows = stmt.execute(rusqlite::params![id]).map_err(|e| format!("Failed to execute delete: {}", e))?;

    if rows == 0 {
        return Err(format!("Book with id '{}' not found", id));
    }

    Ok(())
}

fn book_from_row(row: &rusqlite::Row) -> Book {
    Book {
        id: row.get(0).unwrap(),
        title: row.get(1).unwrap(),
        author: row.get(2).unwrap(),
        year: row.get(3).unwrap_or(None),
        isbn: row.get(4).unwrap_or(None),
        created_at: row.get(5).unwrap(),
        updated_at: row.get(6).unwrap(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn get_test_conn() -> Connection {
        let conn = rusqlite::Connection::open_in_memory().unwrap();
        conn.execute_batch(crate::models::TABLE_DEF).unwrap();
        conn
    }

    #[test]
    fn test_create_book_success() {
        let conn = get_test_conn();
        let req = CreateBookRequest {
            title: Some("The Great Gatsby".to_string()),
            author: Some("F. Scott Fitzgerald".to_string()),
            year: Some(1925),
            isbn: Some("978-0743273565".to_string()),
        };
        let book = create_book(&conn, &req).unwrap();
        assert_eq!(book.title, "The Great Gatsby");
        assert_eq!(book.author, "F. Scott Fitzgerald");
        assert_eq!(book.year, Some(1925));
        assert_eq!(book.isbn, Some("978-0743273565".to_string()));
        assert!(!book.id.is_empty());
    }

    #[test]
    fn test_create_book_missing_title() {
        let conn = get_test_conn();
        let req = CreateBookRequest {
            title: None,
            author: Some("F. Scott Fitzgerald".to_string()),
            year: None,
            isbn: None,
        };
        let result = create_book(&conn, &req);
        assert!(result.is_err());
        assert_eq!(result.unwrap_err(), "title is required");
    }

    #[test]
    fn test_create_book_missing_author() {
        let conn = get_test_conn();
        let req = CreateBookRequest {
            title: Some("The Great Gatsby".to_string()),
            author: None,
            year: None,
            isbn: None,
        };
        let result = create_book(&conn, &req);
        assert!(result.is_err());
        assert_eq!(result.unwrap_err(), "author is required");
    }

    #[test]
    fn test_create_book_empty_title() {
        let conn = get_test_conn();
        let req = CreateBookRequest {
            title: Some("  ".to_string()),
            author: Some("F. Scott Fitzgerald".to_string()),
            year: None,
            isbn: None,
        };
        let result = create_book(&conn, &req);
        assert!(result.is_err());
        assert_eq!(result.unwrap_err(), "title cannot be empty");
    }

    #[test]
    fn test_list_books() {
        let conn = get_test_conn();
        let req1 = CreateBookRequest {
            title: Some("1984".to_string()),
            author: Some("George Orwell".to_string()),
            year: Some(1949),
            isbn: None,
        };
        let req2 = CreateBookRequest {
            title: Some("Animal Farm".to_string()),
            author: Some("George Orwell".to_string()),
            year: Some(1945),
            isbn: None,
        };
        let req3 = CreateBookRequest {
            title: Some("Brave New World".to_string()),
            author: Some("Aldous Huxley".to_string()),
            year: Some(1932),
            isbn: None,
        };
        create_book(&conn, &req1).unwrap();
        create_book(&conn, &req2).unwrap();
        create_book(&conn, &req3).unwrap();

        let books = list_books(&conn, None).unwrap();
        assert_eq!(books.len(), 3);

        // Test author filter
        let filtered = list_books(&conn, Some("Orwell")).unwrap();
        assert_eq!(filtered.len(), 2);
        for book in &filtered {
            assert!(book.author.contains("Orwell"));
        }
    }

    #[test]
    fn test_get_book_by_id_not_found() {
        let conn = get_test_conn();
        let result = get_book_by_id(&conn, "nonexistent-id");
        assert!(result.is_err());
    }

    #[test]
    fn test_update_book() {
        let conn = get_test_conn();
        let create_req = CreateBookRequest {
            title: Some("1984".to_string()),
            author: Some("George Orwell".to_string()),
            year: Some(1949),
            isbn: None,
        };
        let book = create_book(&conn, &create_req).unwrap();
        let id = book.id.clone();

        let update_req = UpdateBookRequest {
            title: Some("1984 - Updated".to_string()),
            author: None,
            year: None,
            isbn: Some("978-0451524935".to_string()),
        };
        let updated = update_book(&conn, &id, &update_req).unwrap();
        assert_eq!(updated.title, "1984 - Updated");
        assert_eq!(updated.author, "George Orwell"); // unchanged
        assert_eq!(updated.isbn, Some("978-0451524935".to_string()));
    }

    #[test]
    fn test_delete_book() {
        let conn = get_test_conn();
        let req = CreateBookRequest {
            title: Some("1984".to_string()),
            author: Some("George Orwell".to_string()),
            year: None,
            isbn: None,
        };
        let book = create_book(&conn, &req).unwrap();
        let id = book.id.clone();

        delete_book(&conn, &id).unwrap();

        let result = get_book_by_id(&conn, &id);
        assert!(result.is_err());
    }

    #[test]
    fn test_delete_book_not_found() {
        let conn = get_test_conn();
        let result = delete_book(&conn, "nonexistent-id");
        assert!(result.is_err());
    }

    #[test]
    fn test_list_books_empty() {
        let conn = get_test_conn();
        let books = list_books(&conn, None).unwrap();
        assert_eq!(books.len(), 0);
    }

    #[test]
    fn test_list_books_with_author_filter_no_match() {
        let conn = get_test_conn();
        let req = CreateBookRequest {
            title: Some("1984".to_string()),
            author: Some("George Orwell".to_string()),
            year: None,
            isbn: None,
        };
        create_book(&conn, &req).unwrap();

        let filtered = list_books(&conn, Some("Nonexistent")).unwrap();
        assert_eq!(filtered.len(), 0);
    }
}
