package com.example.books;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

/**
 * Request body for creating or updating a book.
 *
 * @param title  required title
 * @param author required author
 * @param year   publication year (optional)
 * @param isbn   ISBN (optional)
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record BookInput(String title, String author, Integer year, String isbn) {

    /** Lowest year accepted; earlier dates are rejected as typos. */
    static final int MIN_YEAR = 1400;

    /** Highest year accepted. */
    static final int MAX_YEAR = 2100;

    /**
     * Validates the input.
     *
     * @return a list of human-readable problems; empty when the input is valid
     */
    public java.util.List<String> validate() {
        var errors = new java.util.ArrayList<String>();
        if (title == null || title.isBlank()) {
            errors.add("title is required");
        }
        if (author == null || author.isBlank()) {
            errors.add("author is required");
        }
        if (year != null && (year < MIN_YEAR || year > MAX_YEAR)) {
            errors.add("year must be between " + MIN_YEAR + " and " + MAX_YEAR);
        }
        if (isbn != null && !isbn.isBlank() && !isbn.matches("[0-9Xx-]{10,17}")) {
            errors.add("isbn must be 10 or 13 digits (hyphens allowed)");
        }
        return errors;
    }
}
