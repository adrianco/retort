use actix_web::{web, App, HttpServer};
use serde::{Deserialize, Serialize};
use sqlx::{sqlite::SqlitePoolOptions, Pool, Sqlite};

#[derive(Clone)]
pub struct AppState {
    pub pool: Pool<Sqlite>,
}

#[derive(Serialize)]
pub struct HealthResponse {
    pub status: String,
    pub timestamp: u64,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Book {
    pub id: Option<i64>,
    pub title: String,
    pub author: String,
    pub year: i32,
    pub isbn: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct CreateBookRequest {
    pub title: String,
    pub author: String,
    pub year: i32,
    pub isbn: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct UpdateBookRequest {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

impl Book {
    pub fn with_id(self, id: i64) -> Book {
        Book {
            id: Some(id),
            ..self
        }
    }
}

pub async fn get_pool() -> Pool<Sqlite> {
    let database_url = std::env::var("DATABASE_URL")
        .unwrap_or_else(|_| "sqlite://data.db".to_string());

    SqlitePoolOptions::new()
        .max_connections(5)
        .connect(&database_url)
        .await
        .expect("Failed to create pool")
}

pub async fn migrate(pool: &Pool<Sqlite>) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER NOT NULL,
            isbn TEXT NOT NULL UNIQUE
        )
        "#
    )
    .execute(pool)
    .await?;

    Ok(())
}

async fn health() -> actix_web::HttpResponse {
    actix_web::HttpResponse::Ok().json(HealthResponse {
        status: "ok".to_string(),
        timestamp: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs(),
    })
}

async fn list_books(
    state: web::Data<AppState>,
    query: web::Query<serde_json::Value>,
) -> actix_web::HttpResponse {
    let author_filter = query.get("author").and_then(|v| v.as_str());
    
    let books = if let Some(author) = author_filter {
        sqlx::query_as::<_, Book>(
            "SELECT id, title, author, year, isbn FROM books WHERE author = ?"
        )
        .bind(author)
        .fetch_all(&state.pool)
        .await
    } else {
        sqlx::query_as::<_, Book>(
            "SELECT id, title, author, year, isbn FROM books"
        )
        .fetch_all(&state.pool)
        .await
    };

    match books {
        Ok(books) => actix_web::HttpResponse::Ok().json(books),
        Err(e) => actix_web::HttpResponse::InternalServerError().json(serde_json::json!({
            "error": e.to_string()
        })),
    }
}

async fn create_book(
    state: web::Data<AppState>,
    book: web::Json<CreateBookRequest>,
) -> actix_web::HttpResponse {
    // Basic validation
    if book.title.trim().is_empty() {
        return actix_web::HttpResponse::BadRequest().json(serde_json::json!({"error": "title is required"}));
    }
    if book.author.trim().is_empty() {
        return actix_web::HttpResponse::BadRequest().json(serde_json::json!({"error": "author is required"}));
    }

    let row = match sqlx::query(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING id, title, author, year, isbn"
    )
    .bind(&book.title)
    .bind(&book.author)
    .bind(&book.year)
    .bind(&book.isbn)
    .fetch_one(&state.pool)
    .await {
        Ok(r) => r,
        Err(e) => return actix_web::HttpResponse::InternalServerError().json(serde_json::json!({"error": e.to_string()})),
    };

    let book = Book {
        id: Some(row.get("id")),
        title: row.get("title"),
        author: row.get("author"),
        year: row.get("year"),
        isbn: row.get("isbn"),
    };

    actix_web::HttpResponse::Created().json(book)
}

async fn get_book(
    state: web::Data<AppState>,
    path: web::Path<i64>,
) -> actix_web::HttpResponse {
    let id = path.into_inner();
    
    let book = match sqlx::query_as::<_, Book>(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?"
    )
    .bind(id)
    .fetch_optional(&state.pool)
    .await {
        Ok(b) => b,
        Err(e) => return actix_web::HttpResponse::InternalServerError().json(serde_json::json!({"error": e.to_string()})),
    };

    match book {
        Some(book) => actix_web::HttpResponse::Ok().json(book),
        None => actix_web::HttpResponse::NotFound().json(serde_json::json!({
            "error": format!("Book with id {} not found", id)
        })),
    }
}

async fn update_book(
    state: web::Data<AppState>,
    path: web::Path<i64>,
    updates: web::Json<UpdateBookRequest>,
) -> actix_web::HttpResponse {
    let id = path.into_inner();
    
    // Check if book exists
    let exists = match sqlx::query_as::<_, Book>(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?"
    )
    .bind(id)
    .fetch_optional(&state.pool)
    .await {
        Ok(b) => b,
        Err(e) => return actix_web::HttpResponse::InternalServerError().json(serde_json::json!({"error": e.to_string()})),
    };

    let book = match exists {
        Some(_book) => {
            // Build dynamic update query
            let mut query = String::from("UPDATE books SET ");
            let mut params: Vec<String> = Vec::new();
            
            if let Some(title) = &updates.title {
                query.push_str("title = ?, ");
                params.push(title.clone());
            }
            if let Some(author) = &updates.author {
                query.push_str("author = ?, ");
                params.push(author.clone());
            }
            if let Some(year) = updates.year {
                query.push_str("year = ?, ");
                params.push(year.to_string());
            }
            if let Some(isbn) = &updates.isbn {
                query.push_str("isbn = ?, ");
                params.push(isbn.clone());
            }
            
            // Remove trailing comma and space
            if !params.is_empty() {
                query.pop(); // Remove last ', '
                query.pop(); // Remove last ' '
                query.push_str(" WHERE id = ?");
                params.push(id.to_string());
                
                let book: Book = match sqlx::query_as(&query)
                    .bind(&params[0])
                    .fetch_one(&state.pool)
                    .await {
                        Ok(b) => b,
                        Err(e) => return actix_web::HttpResponse::InternalServerError().json(serde_json::json!({"error": e.to_string()})),
                    };
                
                book
            } else {
                actix_web::HttpResponse::Ok().json(Book {
                    id: Some(id),
                    title: String::new(),
                    author: String::new(),
                    year: 0,
                    isbn: String::new(),
                })
            }
        }
        None => actix_web::HttpResponse::NotFound().json(serde_json::json!({
            "error": format!("Book with id {} not found", id)
        })),
    };

    actix_web::HttpResponse::Ok().json(book)
}

async fn delete_book(
    state: web::Data<AppState>,
    path: web::Path<i64>,
) -> actix_web::HttpResponse {
    let id = path.into_inner();
    
    let result = match sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(id)
        .execute(&state.pool)
        .await {
            Ok(r) => r,
            Err(e) => return actix_web::HttpResponse::InternalServerError().json(serde_json::json!({"error": e.to_string()})),
        };

    if result.rows_affected() == 0 {
        return actix_web::HttpResponse::NotFound().json(serde_json::json!({
            "error": format!("Book with id {} not found", id)
        }));
    }

    actix_web::HttpResponse::NoContent().finish()
}

pub fn configure_routes(cfg: &mut web::ServiceConfig) {
    cfg.service(
        web::scope("/books")
            .route("", web::post().to(create_book))
            .route("", web::get().to(list_books))
            .route("/{id}", web::get().to(get_book))
            .route("/{id}", web::put().to(update_book))
            .route("/{id}", web::delete().to(delete_book))
    );
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init_from_env(env_logger::Env::new().default_filter_or("info"));

    let pool = get_pool().await;

    // Run migrations
    migrate(&pool).await.expect("Failed to run migrations");

    log::info!("Starting server on http://127.0.0.1:8080");

    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(AppState {
                pool: pool.clone(),
            }))
            .route("/health", web::get().to(health))
            .configure(configure_routes)
    })
    .bind("127.0.0.1:8080")?
    .run()
    .await
}
