use crate::db::AppState;
use crate::models::{Book, CreateBookRequest, UpdateBookRequest, validate_book_request, validate_update_request};
use crate::AppError;
use actix_web::{web, HttpResponse};
use serde::Deserialize;

#[derive(Deserialize)]
pub struct QueryParams {
    pub author: Option<String>,
}

pub async fn get_books(
    state: web::Data<AppState>,
    query: web::Query<QueryParams>,
) -> Result<HttpResponse, AppError> {
    let author = &query.author;

    let books = if let Some(author_param) = author {
        sqlx::query_as::<_, Book>("SELECT * FROM books WHERE author = ?")
            .bind(author_param)
            .fetch_all(&state.pool)
            .await?
    } else {
        sqlx::query_as::<_, Book>("SELECT * FROM books")
            .fetch_all(&state.pool)
            .await?
    };

    Ok(HttpResponse::Ok().json(books))
}

pub async fn get_book(
    state: web::Data<AppState>,
    path: web::Path<i64>,
) -> Result<HttpResponse, AppError> {
    let id = path.into_inner();

    let book = sqlx::query_as::<_, Book>("SELECT * FROM books WHERE id = ?")
        .bind(id)
        .fetch_one(&state.pool)
        .await
        .map_err(|_| AppError::NotFound)?;

    Ok(HttpResponse::Ok().json(book))
}

pub async fn create_book(
    state: web::Data<AppState>,
    body: web::Json<CreateBookRequest>,
) -> Result<HttpResponse, AppError> {
    let body = body.into_inner();

    // Validate input
    validate_book_request(&body).map_err(|e| {
        AppError::Validation(e)
    })?;

    let book = sqlx::query_as::<_, Book>(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING *",
    )
    .bind(&body.title)
    .bind(&body.author)
    .bind(body.year)
    .bind(&body.isbn)
    .fetch_one(&state.pool)
    .await?;

    Ok(HttpResponse::Created().json(book))
}

pub async fn update_book(
    state: web::Data<AppState>,
    path: web::Path<i64>,
    body: web::Json<UpdateBookRequest>,
) -> Result<HttpResponse, AppError> {
    let id = path.into_inner();
    let body = body.into_inner();

    // Check if book exists
    let exists = sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM books WHERE id = ?")
        .bind(id)
        .fetch_one(&state.pool)
        .await
        .map_err(|_| AppError::NotFound)?;

    if exists == 0 {
        return Err(AppError::NotFound);
    }

    // Validate input
    validate_update_request(&body).map_err(|e| {
        AppError::Validation(e)
    })?;

    // Build dynamic update query based on which fields are provided
    let book = if body.title.is_some() && body.author.is_some() && body.year.is_some() && body.isbn.is_some() {
        // All fields provided
        sqlx::query_as::<_, Book>(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ? RETURNING *"
        )
        .bind(&body.title.unwrap())
        .bind(&body.author.unwrap())
        .bind(body.year.unwrap())
        .bind(&body.isbn.unwrap())
        .bind(id)
        .fetch_one(&state.pool)
        .await?
    } else if body.title.is_some() && body.author.is_some() && body.year.is_some() {
        // title, author, year
        sqlx::query_as::<_, Book>(
            "UPDATE books SET title = ?, author = ?, year = ? WHERE id = ? RETURNING *"
        )
        .bind(&body.title.unwrap())
        .bind(&body.author.unwrap())
        .bind(body.year.unwrap())
        .bind(id)
        .fetch_one(&state.pool)
        .await?
    } else if body.title.is_some() && body.author.is_some() && body.isbn.is_some() {
        // title, author, isbn
        sqlx::query_as::<_, Book>(
            "UPDATE books SET title = ?, author = ?, isbn = ? WHERE id = ? RETURNING *"
        )
        .bind(&body.title.unwrap())
        .bind(&body.author.unwrap())
        .bind(&body.isbn.unwrap())
        .bind(id)
        .fetch_one(&state.pool)
        .await?
    } else if body.title.is_some() && body.year.is_some() && body.isbn.is_some() {
        // title, year, isbn
        sqlx::query_as::<_, Book>(
            "UPDATE books SET title = ?, year = ?, isbn = ? WHERE id = ? RETURNING *"
        )
        .bind(&body.title.unwrap())
        .bind(body.year.unwrap())
        .bind(&body.isbn.unwrap())
        .bind(id)
        .fetch_one(&state.pool)
        .await?
    } else if body.author.is_some() && body.year.is_some() && body.isbn.is_some() {
        // author, year, isbn
        sqlx::query_as::<_, Book>(
            "UPDATE books SET author = ?, year = ?, isbn = ? WHERE id = ? RETURNING *"
        )
        .bind(&body.author.unwrap())
        .bind(body.year.unwrap())
        .bind(&body.isbn.unwrap())
        .bind(id)
        .fetch_one(&state.pool)
        .await?
    } else if body.title.is_some() && body.author.is_some() {
        // title, author
        sqlx::query_as::<_, Book>(
            "UPDATE books SET title = ?, author = ? WHERE id = ? RETURNING *"
        )
        .bind(&body.title.unwrap())
        .bind(&body.author.unwrap())
        .bind(id)
        .fetch_one(&state.pool)
        .await?
    } else if body.title.is_some() && body.year.is_some() {
        // title, year
        sqlx::query_as::<_, Book>(
            "UPDATE books SET title = ?, year = ? WHERE id = ? RETURNING *"
        )
        .bind(&body.title.unwrap())
        .bind(body.year.unwrap())
        .bind(id)
        .fetch_one(&state.pool)
        .await?
    } else if body.title.is_some() && body.isbn.is_some() {
        // title, isbn
        sqlx::query_as::<_, Book>(
            "UPDATE books SET title = ?, isbn = ? WHERE id = ? RETURNING *"
        )
        .bind(&body.title.unwrap())
        .bind(&body.isbn.unwrap())
        .bind(id)
        .fetch_one(&state.pool)
        .await?
    } else if body.author.is_some() && body.year.is_some() {
        // author, year
        sqlx::query_as::<_, Book>(
            "UPDATE books SET author = ?, year = ? WHERE id = ? RETURNING *"
        )
        .bind(&body.author.unwrap())
        .bind(body.year.unwrap())
        .bind(id)
        .fetch_one(&state.pool)
        .await?
    } else if body.author.is_some() && body.isbn.is_some() {
        // author, isbn
        sqlx::query_as::<_, Book>(
            "UPDATE books SET author = ?, isbn = ? WHERE id = ? RETURNING *"
        )
        .bind(&body.author.unwrap())
        .bind(&body.isbn.unwrap())
        .bind(id)
        .fetch_one(&state.pool)
        .await?
    } else if body.year.is_some() && body.isbn.is_some() {
        // year, isbn
        sqlx::query_as::<_, Book>(
            "UPDATE books SET year = ?, isbn = ? WHERE id = ? RETURNING *"
        )
        .bind(body.year.unwrap())
        .bind(&body.isbn.unwrap())
        .bind(id)
        .fetch_one(&state.pool)
        .await?
    } else if body.title.is_some() {
        // title only
        sqlx::query_as::<_, Book>(
            "UPDATE books SET title = ? WHERE id = ? RETURNING *"
        )
        .bind(&body.title.unwrap())
        .bind(id)
        .fetch_one(&state.pool)
        .await?
    } else if body.author.is_some() {
        // author only
        sqlx::query_as::<_, Book>(
            "UPDATE books SET author = ? WHERE id = ? RETURNING *"
        )
        .bind(&body.author.unwrap())
        .bind(id)
        .fetch_one(&state.pool)
        .await?
    } else if body.year.is_some() {
        // year only
        sqlx::query_as::<_, Book>(
            "UPDATE books SET year = ? WHERE id = ? RETURNING *"
        )
        .bind(body.year.unwrap())
        .bind(id)
        .fetch_one(&state.pool)
        .await?
    } else {
        // isbn only
        sqlx::query_as::<_, Book>(
            "UPDATE books SET isbn = ? WHERE id = ? RETURNING *"
        )
        .bind(&body.isbn.unwrap())
        .bind(id)
        .fetch_one(&state.pool)
        .await?
    };

    Ok(HttpResponse::Ok().json(book))
}

pub async fn delete_book(
    state: web::Data<AppState>,
    path: web::Path<i64>,
) -> Result<HttpResponse, AppError> {
    let id = path.into_inner();

    let deleted = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(id)
        .execute(&state.pool)
        .await?;

    if deleted.rows_affected() == 0 {
        return Err(AppError::NotFound);
    }

    Ok(HttpResponse::NoContent().finish())
}

pub async fn health() -> Result<HttpResponse, AppError> {
    Ok(HttpResponse::Ok().json(serde_json::json!({
        "status": "ok",
        "timestamp": chrono::Utc::now().to_rfc3339()
    })))
}

pub fn configure_routes(cfg: &mut web::ServiceConfig) {
    cfg.service(
        web::scope("")
            .route("/health", web::get().to(health))
            .service(
                web::scope("/books")
                    .route("", web::get().to(get_books))
                    .route("", web::post().to(create_book))
                    .route("/{id}", web::get().to(get_book))
                    .route("/{id}", web::put().to(update_book))
                    .route("/{id}", web::delete().to(delete_book))
            )
    );
}
