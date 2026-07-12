use actix_web::{web, App, HttpServer, HttpResponse, test, ResponseError};
use serde_json::json;
use sqlx::sqlite::SqlitePoolOptions;
use sqlx::SqlitePool;
use uuid::Uuid;
use validator::Validate;

#[derive(serde::Serialize, serde::Deserialize, Validate, Clone)]
struct Book {
    id: Option<Uuid>,
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

async fn create_book(
    pool: web::Data<SqlitePool>,
    book: web::Json<Book>
) -> Result<HttpResponse, actix_web::Error> {
    if !book.validate()? {
        return Ok(HttpResponse::BadRequest().json("Invalid input"));
    }

    let query = "INSERT INTO books (id, title, author, year, isbn) VALUES ($1, $2, $3, $4, $5)";
    sqlx::query(query)
        .bind(&book.id.unwrap_or_else(Uuid::new_v4))
        .bind(&book.title)
        .bind(&book.author)
        .bind(&book.year)
        .bind(&book.isbn)
        .execute(&**pool)
        .await?;

    Ok(HttpResponse::Created().json(book))
}

async fn get_books(
    pool: web::Data<SqlitePool>,
    author: web::Query<Option<String>>
) -> Result<HttpResponse, actix_web::Error> {
    let mut query = String::from("SELECT * FROM books");
    if let Some(author_filter) = author.into_inner() {
        query.push_str(" WHERE author LIKE ?");
        let rows = sqlx::query_as::<_, Book>(&query)
            .bind(format!("%{}%", author_filter))
            .fetch_all(&**pool)
            .await?;
        Ok(HttpResponse::Ok().json(rows))
    } else {
        let rows = sqlx::query_as::<_, Book>(&query)
            .fetch_all(&**pool)
            .await?;
        Ok(HttpResponse::Ok().json(rows))
    }
}

async fn get_book(
    pool: web::Data<SqlitePool>,
    book_id: web::Path<Uuid>
) -> Result<HttpResponse, actix_web::Error> {
    let row = sqlx::query_as::<_, Book>("SELECT * FROM books WHERE id = ?")
        .bind(book_id.into_inner())
        .fetch_one(&**pool)
        .await?;
    Ok(HttpResponse::Ok().json(row))
}

async fn update_book(
    pool: web::Data<SqlitePool>,
    book_id: web::Path<Uuid>,
    book: web::Json<Book>
) -> Result<HttpResponse, actix_web::Error> {
    if !book.validate()? {
        return Ok(HttpResponse::BadRequest().json("Invalid input"));
    }

    let query = "UPDATE books SET title = $1, author = $2, year = $3, isbn = $4 WHERE id = $5";
    sqlx::query(query)
        .bind(&book.title)
        .bind(&book.author)
        .bind(&book.year)
        .bind(&book.isbn)
        .bind(book_id.into_inner())
        .execute(&**pool)
        .await?;

    Ok(HttpResponse::Ok().json(book))
}

async fn delete_book(
    pool: web::Data<SqlitePool>,
    book_id: web::Path<Uuid>
) -> Result<HttpResponse, actix_web::Error> {
    sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(book_id.into_inner())
        .execute(&**pool)
        .await?;

    Ok(HttpResponse::Ok().json({"result": "Book deleted"}))
}

async fn health_check() -> HttpResponse {
    HttpResponse::Ok().json({"status": "healthy"})
}

#[actix_rt::test]
async fn test_api() {
    // Initialize database
    let pool = SqlitePoolOptions::new()
        .max_connections(5)
        .connect("sqlite::memory:")
        .await
        .expect("Failed to create pool.");

    // Create tables
    sqlx::query(
        "CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )"
    )
    .execute(&pool)
    .await
    .expect("Failed to create table");

    // Create test server
    let server = test::init_service(
        App::new()
            .app_data(web::Data::new(pool.clone()))
            .route("/health", web::get().to(health_check))
            .route("/books", web::post().to(create_book))
            .route("/books", web::get().to(get_books))
            .route("/books/{id}", web::get().to(get_book))
            .route("/books/{id}", web::put().to(update_book))
            .route("/books/{id}", web::delete().to(delete_book))
    ).await;

    // Test health check
    let req = test::TestRequest::get().uri("/health").to_request();
    let resp = test::call_service(&server, req).await;
    assert_eq!(resp.status(), 200);

    // Test create book
    let book = Book {
        id: None,
        title: "Test Book".to_string(),
        author: "Test Author".to_string(),
        year: Some(2023),
        isbn: Some("1234567890".to_string()),
    };
    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(&book)
        .to_request();
    let resp = test::call_service(&server, req).await;
    assert_eq!(resp.status(), 201);
    let body = test::read_body(resp).await;
    let created_book: Book = serde_json::from_slice(&body).unwrap();
    assert!(!created_book.id.is_none());

    // Test get book by id
    let req = test::TestRequest::get()
        .uri(&format!("/books/{}", created_book.id.unwrap()))
        .to_request();
    let resp = test::call_service(&server, req).await;
    assert_eq!(resp.status(), 200);

    // Test get all books
    let req = test::TestRequest::get().uri("/books").to_request();
    let resp = test::call_service(&server, req).await;
    assert_eq!(resp.status(), 200);

    // Test update book
    let updated_book = Book {
        id: created_book.id,
        title: "Updated Book".to_string(),
        author: "Updated Author".to_string(),
        year: Some(2024),
        isbn: Some("0987654321".to_string()),
    };
    let req = test::TestRequest::put()
        .uri(&format!("/books/{}", created_book.id.unwrap()))
        .set_json(&updated_book)
        .to_request();
    let resp = test::call_service(&server, req).await;
    assert_eq!(resp.status(), 200);

    // Test delete book
    let req = test::TestRequest::delete()
        .uri(&format!("/books/{}", created_book.id.unwrap()))
        .to_request();
    let resp = test::call_service(&server, req).await;
    assert_eq!(resp.status(), 200);
}
