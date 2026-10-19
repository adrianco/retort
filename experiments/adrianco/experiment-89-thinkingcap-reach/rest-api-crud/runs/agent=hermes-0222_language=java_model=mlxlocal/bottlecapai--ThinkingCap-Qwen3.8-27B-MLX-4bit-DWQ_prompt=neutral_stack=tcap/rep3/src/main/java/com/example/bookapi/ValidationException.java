package com.example.bookapi;

/** Thrown when a request payload fails validation. Mapped to HTTP 400. */
public class ValidationException extends RuntimeException {

    public ValidationException(String message) {
        super(message);
    }
}
