package com.example.books;

/**
 * Exception carrying an HTTP status code, thrown from the service layer
 * when a request cannot be fulfilled (validation failure, missing resource, ...).
 */
public class BookException extends RuntimeException {

    private final int status;

    public BookException(int status, String message) {
        super(message);
        this.status = status;
    }

    public int status() {
        return status;
    }
}
