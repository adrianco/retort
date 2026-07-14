use actix_web::test::TestRequest;
use actix_web::{test, web, App};
use diesel::prelude::*;
use diesel::sqlite::SqliteConnection;
use serde_json::json;
use uuid::Uuid;

mod common;
use common::*;

#[actix_web::test]
async fn test_create_and_list_books() {
    let db = establish_connection();
    let db = web::Data::new(db);

    let app = test::init_service(
        App::new().app_data(db.clone()).route("/books", web::post().to(create_book))
            .route("/books", web::get().to(list_books)),
    ).await;

    // Create a book
    let req = TestRequest::post().uri("/books").set_json(&json!({
        "title": "1984",
        "author": "George Orwell",
        "year": 1949,
        "isbn": "0451524934"
    })).to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 201);

    // List books
    let req = TestRequest::get().uri("/books").to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);
    let body = test::read_body(resp).await;
    assert!(body.contains("1984"));
    assert!(body.contains("George Orwell"));
}

#[actix_web::test]
async fn test_get_book() {
    let db = establish_connection();
    let db = web::Data::new(db);

    // First create a book
    let new_book = NewBook::new("To Kill a Mockingbird", "Harper Lee", Some(1960), Some("0061120081"));
    let connection = &*db;
    diesel::insert_into(books).values(&new_book).execute(connection).unwrap();

    let app = test::init_service(
        App::new().app_data(db.clone()).route("/books/{id}", web::get().to(get_book)),
    ).await;

    // Get the book
    let book_id = books.order(id.desc()).first::<Book>(connection).unwrap().id;
    let req = TestRequest::get().uri("/books/".to_owned() + &book_id.to_string()).to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);
    let body = test::read_body(resp).await;
    assert!(body.contains("To Kill a Mockingbird"));
}

#[actix_web::test]
async fn test_delete_book() {
    let db = establish_connection();
    let db = web::Data::new(db);

    // First create a book
    let new_book = NewBook::new("The Great Gatsby", "F. Scott Fitzgerald", Some(1925), Some("0743273567"));
    let connection = &*db;
    diesel::insert_into(books).values(&new_book).execute(connection).unwrap();

    let app = test::init_service(
        App::new().app_data(db.clone()).route("/books/{id}", web::delete().to(delete_book)),
    ).await;

    // Get the book ID
    let book_id = books.order(id.desc()).first::<Book>(connection).unwrap().id;

    // Delete the book
    let req = TestRequest::delete().uri("/books/".to_owned() + &book_id.to_string()).to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);

    // Verify it's deleted
    let req = TestRequest::get().uri("/books/".to_owned() + &book_id.to_string()).to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 404);
}
