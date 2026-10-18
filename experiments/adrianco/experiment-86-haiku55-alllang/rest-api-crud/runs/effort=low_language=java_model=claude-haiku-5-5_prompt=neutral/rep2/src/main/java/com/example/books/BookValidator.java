package com.example.books;

import java.util.ArrayList;
import java.util.List;

/**
 * Validates book input. Title and author are required; year and isbn are optional
 * but must be well-formed when present.
 */
public final class BookValidator {

    static final int MIN_YEAR = 0;
    static final int MAX_YEAR = 9999;
    static final int MAX_TEXT_LENGTH = 500;

    private BookValidator() {
    }

    /** Returns a list of human-readable validation errors; empty if the book is valid. */
    public static List<String> validate(Book book) {
        List<String> errors = new ArrayList<>();
        if (book == null) {
            errors.add("book body is required");
            return errors;
        }
        if (isBlank(book.title())) {
            errors.add("title is required");
        } else if (book.title().length() > MAX_TEXT_LENGTH) {
            errors.add("title must be at most " + MAX_TEXT_LENGTH + " characters");
        }
        if (isBlank(book.author())) {
            errors.add("author is required");
        } else if (book.author().length() > MAX_TEXT_LENGTH) {
            errors.add("author must be at most " + MAX_TEXT_LENGTH + " characters");
        }
        if (book.year() != null && (book.year() < MIN_YEAR || book.year() > MAX_YEAR)) {
            errors.add("year must be between " + MIN_YEAR + " and " + MAX_YEAR);
        }
        if (book.isbn() != null && !book.isbn().isBlank()) {
            String digits = book.isbn().replaceAll("[-\\s]", "");
            if (!digits.matches("^(\\d{9}[\\dXx]|\\d{13})$")) {
                errors.add("isbn must be a valid ISBN-10 or ISBN-13");
            }
        }
        return errors;
    }

    private static boolean isBlank(String s) {
        return s == null || s.isBlank();
    }
}
