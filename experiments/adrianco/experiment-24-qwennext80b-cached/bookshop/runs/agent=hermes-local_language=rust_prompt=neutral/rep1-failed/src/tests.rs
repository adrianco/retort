use book_api::*;
use actix_web::{test, web, App};
use std::fs;

#[cfg(test)]
mod tests {
    use book_api::{create_book, get_books, get_book, update_book, delete_book, init_pool, health, Book, CreateBook, UpdateBook};
    use actix_web::{web::Data, test, web::{Path, Json, Query}};
    use std::collections::HashMap;
    use std::fs;

    fn setup_test_db() {
        fs::remove_file("test_books.db").ok();
        let conn = rusqlite::Connection::open("test_books.db").unwrap();
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER NOT NULL,
                isbn TEXT NOT NULL
            )"
        ).unwrap();
    }

    #[test]
    fn test_book_struct() {
        let book = Book {
            id: 1,
            title: "Test Book".to_string(),
            author: "Test Author".to_string(),
            year: 2024,
            isbn: "1234567890".to_string(),
        };

        assert_eq!(book.id, 1);
        assert_eq!(book.title, "Test Book");
        assert_eq!(book.author, "Test Author");
        assert_eq!(book.year, 2024);
        assert_eq!(book.isbn, "1234567890");
    }

    #[test]
    fn test_create_book_validation_title_required() {
        let create_book = CreateBook {
            title: "".to_string(),
            author: "Test Author".to_string(),
            year: 2024,
            isbn: "1234567890".to_string(),
        };

        assert!(create_book.title.is_empty());
    }

    #[test]
    fn test_create_book_validation_author_required() {
        let create_book = CreateBook {
            title: "Test Book".to_string(),
            author: "".to_string(),
            year: 2024,
            isbn: "1234567890".to_string(),
        };

        assert!(create_book.author.is_empty());
    }

    #[actix_web::test]
    async fn test_health_endpoint() {
        let pool = init_pool().await;
        let app = test::init_service(App::new()
            .app_data(Data::new(pool))
            .route("/health", web::get().to(health))
        ).await;

        let req = test::TestRequest::get().uri("/health").to_request();
        let resp = test::call_service(&app, req).await;

        assert_eq!(resp.status(), actix_web::http::StatusCode::OK);
        let body = test::read_body(resp).await;
        let body_str = std::str::from_utf8(&body).unwrap();
        assert!(body_str.contains(r#"{"status":"healthy"}"#));
    }

    #[actix_web::test]
    async fn test_create_and_get_book() {
        setup_test_db();
        let pool = init_pool().await;

        let app = test::init_service(App::new()
            .app_data(Data::new(pool.clone()))
            .route("/books", web::post().to(create_book))
            .route("/books", web::get().to(get_books))
            .route("/books/{id}", web::get().to(get_book))
        ).await;

        let create_request = test::TestRequest::post()
            .uri("/books")
            .set_json(&CreateBook {
                title: "The Rust Programming Language".to_string(),
                author: "Steve Klabnik".to_string(),
                year: 2018,
                isbn: "9781593278281".to_string(),
            })
            .to_request();
        let resp = test::call_service(&app, create_request).await;
        assert_eq!(resp.status(), actix_web::http::StatusCode::CREATED);

        let list_request = test::TestRequest::get().uri("/books").to_request();
        let resp = test::call_service(&app, list_request).await;
        assert_eq!(resp.status(), actix_web::http::StatusCode::OK);

        let get_request = test::TestRequest::get().uri("/books/1").to_request();
        let resp = test::call_service(&app, get_request).await;
        assert_eq!(resp.status(), actix_web::http::StatusCode::OK);
    }

    #[actix_web::test]
    async fn test_update_book() {
        setup_test_db();
        let pool = init_pool().await;

        let app = test::init_service(App::new()
            .app_data(Data::new(pool.clone()))
            .route("/books", web::post().to(create_book))
            .route("/books/{id}", web::put().to(update_book))
        ).await;

        let create_request = test::TestRequest::post()
            .uri("/books")
            .set_json(&CreateBook {
                title: "Original Title".to_string(),
                author: "Original Author".to_string(),
                year: 2018,
                isbn: "9781593278281".to_string(),
            })
            .to_request();
        let resp = test::call_service(&app, create_request).await;
        assert_eq!(resp.status(), actix_web::http::StatusCode::CREATED);

        let update_request = test::TestRequest::put()
            .uri("/books/1")
            .set_json(&UpdateBook {
                title: Some("Updated Title".to_string()),
                author: None,
                year: None,
                isbn: None,
            })
            .to_request();
        let resp = test::call_service(&app, update_request).await;
        assert_eq!(resp.status(), actix_web::http::StatusCode::OK);

        let body: Book = test::read_body_json(resp).await;
        assert_eq!(body.title, "Updated Title");
        assert_eq!(body.author, "Original Author");
    }

    #[actix_web::test]
    async fn test_delete_book() {
        setup_test_db();
        let pool = init_pool().await;

        let app = test::init_service(App::new()
            .app_data(Data::new(pool.clone()))
            .route("/books", web::post().to(create_book))
            .route("/books/{id}", web::delete().to(delete_book))
        ).await;

        let create_request = test::TestRequest::post()
            .uri("/books")
            .set_json(&CreateBook {
                title: "To Delete".to_string(),
                author: "Author".to_string(),
                year: 2018,
                isbn: "9781593278281".to_string(),
            })
            .to_request();
        let resp = test::call_service(&app, create_request).await;
        assert_eq!(resp.status(), actix_web::http::StatusCode::CREATED);

        let delete_request = test::TestRequest::delete().uri("/books/1").to_request();
        let resp = test::call_service(&app, delete_request).await;
        assert_eq!(resp.status(), actix_web::http::StatusCode::NO_CONTENT);
    }

    #[actix_web::test]
    async fn test_404_on_nonexistent_book() {
        setup_test_db();
        let pool = init_pool().await;

        let app = test::init_service(App::new()
            .app_data(Data::new(pool.clone()))
            .route("/books/{id}", web::get().to(get_book))
            .route("/books/{id}", web::put().to(update_book))
            .route("/books/{id}", web::delete().to(delete_book))
        ).await;

        let get_request = test::TestRequest::get().uri("/books/999").to_request();
        let resp = test::call_service(&app, get_request).await;
        assert_eq!(resp.status(), actix_web::http::StatusCode::NOT_FOUND);

        let update_request = test::TestRequest::put()
            .uri("/books/999")
            .set_json(&UpdateBook {
                title: Some("New Title".to_string()),
                author: None,
                year: None,
                isbn: None,
            })
            .to_request();
        let resp = test::call_service(&app, update_request).await;
        assert_eq!(resp.status(), actix_web::http::StatusCode::NOT_FOUND);

        let delete_request = test::TestRequest::delete().uri("/books/999").to_request();
        let resp = test::call_service(&app, delete_request).await;
        assert_eq!(resp.status(), actix_web::http::StatusCode::NOT_FOUND);
    }

    #[actix_web::test]
    async fn test_author_filter() {
        setup_test_db();
        let pool = init_pool().await;

        let app = test::init_service(App::new()
            .app_data(Data::new(pool.clone()))
            .route("/books", web::post().to(create_book))
            .route("/books", web::get().to(get_books))
        ).await;

        let create_request1 = test::TestRequest::post()
            .uri("/books")
            .set_json(&CreateBook {
                title: "Book 1".to_string(),
                author: "Author A".to_string(),
                year: 2018,
                isbn: "111".to_string(),
            })
            .to_request();
        let _resp = test::call_service(&app, create_request1).await;

        let create_request2 = test::TestRequest::post()
            .uri("/books")
            .set_json(&CreateBook {
                title: "Book 2".to_string(),
                author: "Author B".to_string(),
                year: 2019,
                isbn: "222".to_string(),
            })
            .to_request();
        let _resp = test::call_service(&app, create_request2).await;

        let filter_request = test::TestRequest::get()
            .uri("/books?author=Author%20A")
            .to_request();
        let resp = test::call_service(&app, filter_request).await;
        assert_eq!(resp.status(), actix_web::http::StatusCode::OK);

        let books: Vec<Book> = test::read_body_json(resp).await;
        assert_eq!(books.len(), 1);
        assert_eq!(books[0].author, "Author A");
    }
}
