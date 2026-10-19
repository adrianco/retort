package com.example.bookapi;

/**
 * Centralized request validation for book payloads.
 * Title and author are required and must be non-blank.
 */
final class Validation {

    private Validation() {
    }

    /**
     * @throws ValidationException with a human-readable message if the payload is invalid
     */
    static void validateOrThrow(BookRequest request) {
        if (request == null) {
            throw new ValidationException("Request body is required");
        }
        if (isBlank(request.title())) {
            throw new ValidationException("'title' is required");
        }
        if (isBlank(request.author())) {
            throw new ValidationException("'author' is required");
        }
    }

    private static boolean isBlank(String value) {
        return value == null || value.isBlank();
    }
}
