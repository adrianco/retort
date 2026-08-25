use actix_web::{web, App, HttpServer, HttpResponse, Result};
use serde::{Deserialize, Serialize};
use sqlx::{query, SqlitePool, Row};
use validator::Validate;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum AppError {
    #[error("Database error: {0}")]
    Database(#[from] sqlx::Error),
    #[error("Validation error: {0}")]
    Validation(String),
    #[error("Book not found")]
    NotFound,
}

impl From<validator::ValidationErrors> for AppError {
    fn from(err: validator::ValidationErrors) -> Self {
        AppError::Validation(err.to_string())
    }
}

impl actix_web::ResponseError for AppError {
    fn status_code(&self) -> actix_web::http::StatusCode {
        match self {
            AppError::Database(_) => actix_web::http::StatusCode::INTERNAL_SERVER_ERROR,
            AppError::Validation(_) => actix_web::http::StatusCode::BAD_REQUEST,
            AppError::NotFound => actix_web::http::StatusCode::NOT_FOUND,
        }
    }

    fn error_response(&self) -> HttpResponse {
        HttpResponse::build(self.status_code()).json(serde_json::json!({
            "error": self.to_string()
        }))
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: i32,
    pub isbn: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, validator::Validate)]
pub struct BookInput {
    #[validate(length(min = 1))]
    pub title: String,
    #[validate(length(min = 1))]
    pub author: String,
    pub year: i32,
    pub isbn: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BookUpdate {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthResponse {
    pub status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BooksResponse {
    pub books: Vec<Book>,
}

#[derive(Clone)]
pub struct AppState {
    pub pool: SqlitePool,
}

async fn health_check() -> Result<web::Json<HealthResponse>, AppError> {
    Ok(web::Json(HealthResponse {
        status: "ok".to_string(),
    }))
}

async fn list_books(
    query: web::Query<std::collections::HashMap<String, String>>,
    data: web::Data<AppState>,
) -> Result<web::Json<BooksResponse>, AppError> {
    let author_filter = query.get("author").map(|s| s.as_str());
    let books = get_books(&data.pool, author_filter).await?;
    Ok(web::Json(BooksResponse { books }))
}

async fn get_book(
    path: web::Path<i64>,
    data: web::Data<AppState>,
) -> Result<web::Json<Book>, AppError> {
    let book = get_book_by_id(&data.pool, path.into_inner()).await?;
    Ok(web::Json(book))
}

async fn create_book(
    book_input: web::Json<BookInput>,
    data: web::Data<AppState>,
) -> Result<web::Json<Book>, AppError> {
    book_input.validate()?;
    let book = create_book_record(&data.pool, book_input.into_inner()).await?;
    Ok(web::Json(book))
}

async fn update_book(
    path: web::Path<i64>,
    book_update: web::Json<BookUpdate>,
    data: web::Data<AppState>,
) -> Result<web::Json<Book>, AppError> {
    let book = update_book_record(
        &data.pool,
        path.into_inner(),
        book_update.into_inner(),
    )
    .await?;
    Ok(web::Json(book))
}

async fn delete_book(
    path: web::Path<i64>,
    data: web::Data<AppState>,
) -> Result<HttpResponse, AppError> {
    delete_book_record(&data.pool, path.into_inner()).await?;
    Ok(HttpResponse::NoContent().finish())
}

async fn get_books(
    pool: &SqlitePool,
    author_filter: Option<&str>,
) -> Result<Vec<Book>, AppError> {
    let books = if let Some(author) = author_filter {
        query("SELECT id, title, author, year, isbn FROM books WHERE author = ?")
            .bind(author)
            .fetch_all(pool)
            .await?
    } else {
        query("SELECT id, title, author, year, isbn FROM books")
            .fetch_all(pool)
            .await?
    };

    let books: Vec<Book> = books
        .into_iter()
        .map(|row| Book {
            id: row.get(0),
            title: row.get(1),
            author: row.get(2),
            year: row.get(3),
            isbn: row.get(4),
        })
        .collect();

    Ok(books)
}

async fn get_book_by_id(pool: &SqlitePool, id: i64) -> Result<Book, AppError> {
    let book = query("SELECT id, title, author, year, isbn FROM books WHERE id = ?")
        .bind(id)
        .fetch_optional(pool)
        .await?;

    book.map(|row| Book {
        id: row.get(0),
        title: row.get(1),
        author: row.get(2),
        year: row.get(3),
        isbn: row.get(4),
    })
    .ok_or(AppError::NotFound)
}

async fn create_book_record(pool: &SqlitePool, input: BookInput) -> Result<Book, AppError> {
    let record = query(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
    )
    .bind(&input.title)
    .bind(&input.author)
    .bind(input.year)
    .bind(&input.isbn)
    .execute(pool)
    .await?;

    let id = record.last_insert_rowid();

    Ok(Book {
        id,
        title: input.title,
        author: input.author,
        year: input.year,
        isbn: input.isbn,
    })
}

async fn update_book_record(
    pool: &SqlitePool,
    id: i64,
    input: BookUpdate,
) -> Result<Book, AppError> {
    let existing_book = get_book_by_id(pool, id).await?;

    let updated_book = Book {
        id,
        title: input.title.unwrap_or(existing_book.title),
        author: input.author.unwrap_or(existing_book.author),
        year: input.year.unwrap_or(existing_book.year),
        isbn: input.isbn.unwrap_or(existing_book.isbn),
    };

    query(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
    )
    .bind(&updated_book.title)
    .bind(&updated_book.author)
    .bind(updated_book.year)
    .bind(&updated_book.isbn)
    .bind(id)
    .execute(pool)
    .await?;

    Ok(updated_book)
}

async fn delete_book_record(pool: &SqlitePool, id: i64) -> Result<(), AppError> {
    let affected = query("DELETE FROM books WHERE id = ?")
        .bind(id)
        .execute(pool)
        .await?;

    if affected.rows_affected() == 0 {
        return Err(AppError::NotFound);
    }

    Ok(())
}

async fn ensure_schema(pool: &SqlitePool) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER NOT NULL,
            isbn TEXT NOT NULL
        )
        "#
    )
    .execute(pool)
    .await?;

    Ok(())
}

#[actix_web::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    env_logger::init_from_env(env_logger::Env::new().default_filter_or("info"));
    log::info!("Starting Book API server...");

    let pool = SqlitePool::connect("sqlite:books.db").await?;
    ensure_schema(&pool).await?;

    let app_state = web::Data::new(AppState {
        pool,
    });

    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .route("/health", web::get().to(health_check))
            .service(
                web::scope("/books")
                    .route("", web::get().to(list_books))
                    .route("", web::post().to(create_book))
                    .route("/{id}", web::get().to(get_book))
                    .route("/{id}", web::put().to(update_book))
                    .route("/{id}", web::delete().to(delete_book)),
            )
    })
    .bind("127.0.0.1:8080")?
    .run()
    .await?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use actix_web::{test, web, App};

    async fn create_test_app() -> App<impl actix_web::dev::ServiceFactory<
        actix_web::dev::ServiceRequest,
        Config = (),
        Response = actix_web::dev::ServiceResponse,
        Error = actix_web::Error,
        InitError = (),
    >> {
        let pool = SqlitePool::connect("sqlite::memory:").await.unwrap();
        ensure_schema(&pool).await.unwrap();

        let app_state = web::Data::new(AppState {
            pool,
        });

        App::new()
            .app_data(app_state)
            .route("/health", web::get().to(health_check))
            .service(
                web::scope("/books")
                    .route("", web::get().to(list_books))
                    .route("", web::post().to(create_book))
                    .route("/{id}", web::get().to(get_book))
                    .route("/{id}", web::put().to(update_book))
                    .route("/{id}", web::delete().to(delete_book)),
            )
    }

    #[actix_web::test]
    async fn test_health_check() {
        let app = test::init_service(create_test_app().await).await;
        let req = test::TestRequest::get().uri("/health").to_request();
        let resp = test::call_service(&app, req).await;

        assert_eq!(resp.status(), actix_web::http::StatusCode::OK);
    }

    #[actix_web::test]
    async fn test_create_and_get_book() {
        let app = test::init_service(create_test_app().await).await;

        let create_req = test::TestRequest::post()
            .uri("/books")
            .set_json(web::Json(BookInput {
                title: "Test Book".to_string(),
                author: "Test Author".to_string(),
                year: 2024,
                isbn: "1234567890".to_string(),
            }))
            .to_request();

        let body = test::call_and_read_body(&app, create_req).await;
        let resp: Book = serde_json::from_slice(&body).unwrap();
        assert_eq!(resp.title, "Test Book");
        assert_eq!(resp.author, "Test Author");

        let get_req = test::TestRequest::get()
            .uri("/books/1")
            .to_request();

        let body = test::call_and_read_body(&app, get_req).await;
        let book_resp: Book = serde_json::from_slice(&body).unwrap();
        assert_eq!(book_resp.title, "Test Book");
    }

    #[actix_web::test]
    async fn test_list_books_with_filter() {
        let app = test::init_service(create_test_app().await).await;

        let create_req1 = test::TestRequest::post()
            .uri("/books")
            .set_json(web::Json(BookInput {
                title: "Book 1".to_string(),
                author: "Author A".to_string(),
                year: 2020,
                isbn: "111".to_string(),
            }))
            .to_request();

        test::call_service(&app, create_req1).await;

        let create_req2 = test::TestRequest::post()
            .uri("/books")
            .set_json(web::Json(BookInput {
                title: "Book 2".to_string(),
                author: "Author B".to_string(),
                year: 2021,
                isbn: "222".to_string(),
            }))
            .to_request();

        test::call_service(&app, create_req2).await;

        let list_req = test::TestRequest::get()
            .uri("/books?author=Author%20A")
            .to_request();

        let body = test::call_and_read_body(&app, list_req).await;
        let resp: BooksResponse = serde_json::from_slice(&body).unwrap();
        assert_eq!(resp.books.len(), 1);
        assert_eq!(resp.books[0].author, "Author A");
    }

    #[actix_web::test]
    async fn test_update_book() {
        let app = test::init_service(create_test_app().await).await;

        let create_req = test::TestRequest::post()
            .uri("/books")
            .set_json(web::Json(BookInput {
                title: "Original Title".to_string(),
                author: "Original Author".to_string(),
                year: 2020,
                isbn: "000".to_string(),
            }))
            .to_request();

        test::call_service(&app, create_req).await;

        let update_req = test::TestRequest::put()
            .uri("/books/1")
            .set_json(web::Json(BookUpdate {
                title: Some("Updated Title".to_string()),
                author: None,
                year: None,
                isbn: None,
            }))
            .to_request();

        let body = test::call_and_read_body(&app, update_req).await;
        let resp: Book = serde_json::from_slice(&body).unwrap();
        assert_eq!(resp.title, "Updated Title");
        assert_eq!(resp.author, "Original Author");
    }

    #[actix_web::test]
    async fn test_delete_book() {
        let app = test::init_service(create_test_app().await).await;

        let create_req = test::TestRequest::post()
            .uri("/books")
            .set_json(web::Json(BookInput {
                title: "To Delete".to_string(),
                author: "Delete Author".to_string(),
                year: 2020,
                isbn: "999".to_string(),
            }))
            .to_request();

        test::call_service(&app, create_req).await;

        let delete_req = test::TestRequest::delete()
            .uri("/books/1")
            .to_request();

        let resp = test::call_service(&app, delete_req).await;
        assert_eq!(resp.status(), actix_web::http::StatusCode::NO_CONTENT);

        let get_req = test::TestRequest::get()
            .uri("/books/1")
            .to_request();

        let resp2 = test::call_service(&app, get_req).await;
        assert_eq!(resp2.status(), actix_web::http::StatusCode::NOT_FOUND);
    }
}
