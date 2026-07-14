package com.example.books;

/**
 * Thrown when an incoming request fails input validation.
 * Results in an HTTP 400 response.
 */
public class ValidationException extends RuntimeException {
    public ValidationException(String message) {
        super(message);
    }
}
