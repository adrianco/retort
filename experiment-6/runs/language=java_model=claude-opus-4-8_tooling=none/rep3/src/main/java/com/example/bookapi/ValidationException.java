package com.example.bookapi;

/**
 * Thrown when incoming book data fails validation. Maps to HTTP 400.
 */
public class ValidationException extends RuntimeException {
    public ValidationException(String message) {
        super(message);
    }
}
