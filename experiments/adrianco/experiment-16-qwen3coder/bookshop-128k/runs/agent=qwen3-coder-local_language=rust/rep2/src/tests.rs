#[cfg(test)]
mod tests {
    use rocket::local::blocking::Client;
    use rocket::http::{ContentType, Status};
    use serde_json::json;

    #[test]
    fn test_health_check() {
        let client = Client::tracked(rocket::build()).expect("valid rocket instance");
        let response = client.get("/api/health").dispatch();
        assert_eq!(response.status(), Status::Ok);
    }

    #[test]
    fn test_create_and_get_book() {
        let client = Client::tracked(rocket::build()).expect("valid rocket instance");
        
        // Create a book
        let book_data = json!({
            "title": "Test Book",
            "author": "Test Author",
            "year": 2023,
            "isbn": "1234567890"
        });
        
        let response = client
            .post("/api/books")
            .header(ContentType::Json)
            .body(book_data.to_string())
            .dispatch();
            
        assert_eq!(response.status(), Status::Ok);
        
        // Get the book back
        let response = client.get("/api/books").dispatch();
        assert_eq!(response.status(), Status::Ok);
    }

    #[test]
    fn test_create_book_validation() {
        let client = Client::tracked(rocket::build()).expect("valid rocket instance");
        
        // Try to create a book without required fields
        let book_data = json!({
            "title": "",
            "author": "Test Author",
            "year": 2023,
            "isbn": "1234567890"
        });
        
        let response = client
            .post("/api/books")
            .header(ContentType::Json)
            .body(book_data.to_string())
            .dispatch();
            
        assert_eq!(response.status(), Status::BadRequest);
    }
}