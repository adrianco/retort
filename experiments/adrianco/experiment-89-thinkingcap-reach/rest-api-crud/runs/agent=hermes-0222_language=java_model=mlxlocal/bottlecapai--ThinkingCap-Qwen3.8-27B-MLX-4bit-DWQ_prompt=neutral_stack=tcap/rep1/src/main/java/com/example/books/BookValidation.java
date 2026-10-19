package com.example.books;

/**
 * Input validation for book payloads.
 * Title and author are required and must be non-blank.
 */
public final class BookValidation {

    private BookValidation() {
    }

    /**
     * Returns the trimmed value or throws a 400 {@link BookException}.
     */
    public static String require(String value, String field) {
        if (value == null || value.isBlank()) {
            throw new BookException(400, field + " is required");
        }
        return value.trim();
    }

    /**
     * Validates a create/update payload and returns a normalized copy
     * (trimmed title/author). Throws a 400 {@link BookException} on failure.
     */
    public static BookInput validate(BookInput in) {
        if (in == null) {
            throw new BookException(400, "Request body is required");
        }
        String title = require(in.title(), "title");
        String author = require(in.author(), "author");
        return new BookInput(title, author, in.year(), in.isbn());
    }
}
