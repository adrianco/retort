use actix_web::{web, App, HttpResponse};
use serde::{Deserialize, Serialize};
use sqlx::{Pool, Sqlite, FromRow};

// ============================================================
// Models
// ============================================================

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq, FromRow)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct CreateBookRequest {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct UpdateBookRequest {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

// ============================================================
// Database initialization
// ============================================================

pub async fn init_database(db_url: &str) -> Pool<Sqlite> {
    let pool = Pool::<Sqlite>::connect(db_url)
        .await
        .expect("Failed to create database pool");

    sqlx::migrate!("./migrations")
        .run(&pool)
        .await
        .expect("Failed to run migrations");

    pool
}

// ============================================================
// Health check handler
// ============================================================

pub async fn health_check() -> HttpResponse {
    HttpResponse::Ok().json(serde_json::json!({"status": "ok"}))
}

// ============================================================
// Create book handler
// ============================================================

pub async fn create_book(
    pool: web::Data<Pool<Sqlite>>,
    body: web::Json<CreateBookRequest>,
) -> HttpResponse {
    let title = body.title.as_ref().map(|s| s.as_str()).unwrap_or_default();
    let author = body.author.as_ref().map(|s| s.as_str()).unwrap_or_default();

    if title.is_empty() {
        return HttpResponse::BadRequest().json(serde_json::json!({
            "error": "Title is required"
        }));
    }

    if author.is_empty() {
        return HttpResponse::BadRequest().json(serde_json::json!({
            "error": "Author is required"
        }));
    }

    let (id, title, author, year, isbn): (i64, String, String, Option<i32>, Option<String>) = sqlx::query_as(
        r#"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING id, title, author, year, isbn"#
    )
    .bind(&title)
    .bind(&author)
    .bind(body.year)
    .bind(body.isbn.as_deref())
    .fetch_one(&*pool)
    .await
    .map_err(|e| {
        eprintln!("Database error creating book: {}", e);
        HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to create book"}))
    });

    HttpResponse::Created().json(Book { id, title, author, year, isbn })
}

// ============================================================
// List books handler
// ============================================================

pub async fn list_books(
    pool: web::Data<Pool<Sqlite>>,
    query: web::Query<std::collections::HashMap<String, String>>,
) -> HttpResponse {
    let author = query.get("author").cloned();

    let books: Vec<Book> = match author {
        Some(author_filter) => {
            sqlx::query_as::<_, Book>(
                r#"SELECT id, title, author, year, isbn FROM books WHERE author = ?"#
            )
            .bind(&author_filter)
            .fetch_all(&*pool)
            .await
            .map_err(|e| {
                eprintln!("Database error listing books: {}", e);
                HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to list books"}))
            })
            .unwrap_or_default()
        }
        None => {
            sqlx::query_as::<_, Book>(
                r#"SELECT id, title, author, year, isbn FROM books"#
            )
            .fetch_all(&*pool)
            .await
            .map_err(|e| {
                eprintln!("Database error listing books: {}", e);
                HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to list books"}))
            })
            .unwrap_or_default()
        }
    };

    HttpResponse::Ok().json(books)
}

// ============================================================
// Get book handler
// ============================================================

pub async fn get_book(
    pool: web::Data<Pool<Sqlite>>,
    path: web::Path<i64>,
) -> HttpResponse {
    let id = path.into_inner();

    let book: Option<Book> = sqlx::query_as::<_, Book>(
        r#"SELECT id, title, author, year, isbn FROM books WHERE id = ?"#
    )
    .bind(id)
    .fetch_optional(&*pool)
    .await
    .map_err(|e| {
        eprintln!("Database error getting book: {}", e);
        HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to get book"}))
    })
    .unwrap_or(None);

    match book {
        Some(book) => HttpResponse::Ok().json(book),
        None => HttpResponse::NotFound().json(serde_json::json!({"error": "Book not found"})),
    }
}

// ============================================================
// Update book handler
// ============================================================

pub async fn update_book(
    pool: web::Data<Pool<Sqlite>>,
    path: web::Path<i64>,
    body: web::Json<UpdateBookRequest>,
) -> HttpResponse {
    let id = path.into_inner();

    // Check if book exists first
    let existing: Option<Book> = sqlx::query_as::<_, Book>(
        r#"SELECT id, title, author, year, isbn FROM books WHERE id = ?"#
    )
    .bind(id)
    .fetch_optional(&*pool)
    .await
    .map_err(|e| {
        eprintln!("Database error getting book: {}", e);
        HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to get book"}))
    })
    .unwrap_or(None);

    let book = match existing {
        Some(b) => {
            // Validate provided fields
            if let Some(ref title) = body.title {
                if title.is_empty() {
                    return HttpResponse::BadRequest().json(serde_json::json!({"error": "Title is required"}));
                }
            }
            if let Some(ref author) = body.author {
                if author.is_empty() {
                    return HttpResponse::BadRequest().json(serde_json::json!({"error": "Author is required"}));
                }
            }

            let new_title = body.title.as_ref().map(|s| s.as_str()).unwrap_or(&b.title);
            let new_author = body.author.as_ref().map(|s| s.as_str()).unwrap_or(&b.author);
            let new_year = body.year.or(b.year);
            let new_isbn = body.isbn.clone().or(b.isbn);

            let (id, title, author, year, isbn): (i64, String, String, Option<i32>, Option<String>) = sqlx::query_as(
                r#"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ? RETURNING id, title, author, year, isbn"#
            )
            .bind(new_title)
            .bind(new_author)
            .bind(new_year)
            .bind(new_isbn.as_deref())
            .bind(id)
            .fetch_one(&*pool)
            .await
            .map_err(|e| {
                eprintln!("Database error updating book: {}", e);
                HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to update book"}))
            });

            Book { id, title, author, year, isbn }
        }
        None => {
            return HttpResponse::NotFound().json(serde_json::json!({"error": "Book not found"}));
        }
    };

    HttpResponse::Ok().json(book)
}

// ============================================================
// Delete book handler
// ============================================================

pub async fn delete_book(
    pool: web::Data<Pool<Sqlite>>,
    path: web::Path<i64>,
) -> HttpResponse {
    let id = path.into_inner();

    let result = sqlx::query(r#"DELETE FROM books WHERE id = ?"#)
        .bind(id)
        .execute(&*pool)
        .await
        .map_err(|e| {
            eprintln!("Database error deleting book: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to delete book"}))
        });

    match result {
        Ok(r) if r.rows_affected() > 0 => HttpResponse::NoContent().finish(),
        Ok(_) => HttpResponse::NotFound().json(serde_json::json!({"error": "Book not found"})),
        Err(_) => HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to delete book"})),
    }
}

// ============================================================
// App builder
// ============================================================

pub fn create_app(pool: Pool<Sqlite>) -> App {
    App::new()
        .app_data(web::Data::new(pool))
        .route("/health", web::get().to(health_check))
        .route("/books", web::post().to(create_book))
        .route("/books", web::get().to(list_books))
        .route("/books/{id}", web::get().to(get_book))
        .route("/books/{id}", web::put().to(update_book))
        .route("/books/{id}", web::delete().to(delete_book))
}
