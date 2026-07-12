use actix_web::{test, App, HttpResponse, web, HttpServer, Error};
use diesel::prelude::*;
use diesel::sqlite::SqliteConnection;
use dotenv::dotenv;
use serde::Deserialize;
use uuid::Uuid;

mod models;
mod schema;
use models::Book;

#[derive(Deserialize)]
struct BookFilter {
    author: Option<String>,
}

async fn create_book(
    db: web::Data<SqliteConnection>, 
    item: web::Json<Book>
) -> Result<HttpResponse, Error> {
    let new_book = Book {
        id: Uuid::new_v4(),
        ..item.into_inner()
    };
    
    web::block(move || {
        diesel::insert_into(schema::books::table)
            .values(&new_book)
            .execute(&*db)
    }).await.map_err(|_| actix_web::error::ErrorInternalServerError("Error creating book"))?;
    
    Ok(HttpResponse::Created().json(new_book))
}

async fn get_books(
    db: web::Data<SqliteConnection>, 
    query: Query<BookFilter>
) -> Result<HttpResponse, Error> {
    let results = web::block(move || {
        let mut query = schema::books::table.into_boxed::<SqliteConnection>();
        if let Some(author) = &query.author {
            query = query.filter(schema::books::author.eq(author));
        }
        query.load::<Book>(&*db)
    }).await.map_err(|_| actix_web::error::ErrorInternalServerError("Error loading books"))?;
    
    Ok(HttpResponse::Ok().json(results))
}

#[cfg(test)]
mod tests {
    use super::*;
    use actix_rt::Runtime;

    #[actix_rt::test]
    async fn test_create_book() {
        dotenv().ok();
        
        let database_url = std::env::var("DATABASE_URL")
            .expect("DATABASE_URL must be set");
        let connection = SqliteConnection::establish(&database_url)
            .expect(&format!("Error connecting to {}", database_url));
        
        let book = Book {
            id: Uuid::new_v4(),
            title: "Test Book".to_string(),
            author: "Test Author".to_string(),
            year: Some(2021),
            isbn: Some("1234567890".to_string()),
        };
        
        let db = test::init_service(
            App::new()
                .app_data(web::Data::new(connection.clone()))
                .route("/books", web::post().to(create_book))
        ).await;
        
        let resp = test::call_service(
            &db,
            test::TestRequest::post()
                .uri("/books")
                .set_json(&book)
                .to_request(),
        ).await;
        
        assert_eq!(resp.status(), 201);
    }

    #[actix_rt::test]
    async fn test_get_books() {
        dotenv().ok();
        
        let database_url = std::env::var("DATABASE_URL")
            .expect("DATABASE_URL must be set");
        let connection = SqliteConnection::establish(&database_url)
            .expect(&format!("Error connecting to {}", database_url));
        
        let db = test::init_service(
            App::new()
                .app_data(web::Data::new(connection.clone()))
                .route("/books", web::get().to(get_books))
        ).await;
        
        let resp = test::call_service(
            &db,
            test::TestRequest::get().uri("/books").to_request(),
        ).await;
        
        assert_eq!(resp.status(), 200);
    }
}
