package com.example.books;

/** Thrown when request input fails validation; mapped to HTTP 400. */
public class ValidationException extends RuntimeException {
    public ValidationException(String message) {
        super(message);
    }
}
