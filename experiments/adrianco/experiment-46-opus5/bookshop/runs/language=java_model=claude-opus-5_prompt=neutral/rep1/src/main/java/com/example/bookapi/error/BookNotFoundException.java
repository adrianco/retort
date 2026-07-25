package com.example.bookapi.error;

/** Raised when a book id does not exist; mapped to HTTP 404. */
public class BookNotFoundException extends RuntimeException {

    public BookNotFoundException(long id) {
        super("Book " + id + " not found");
    }
}
