package com.example.books;

import java.time.Year;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

/**
 * Validates and normalises {@link BookRequest} input.
 */
public final class BookValidator {

    private static final Pattern ISBN_CHARS = Pattern.compile("[0-9Xx-]+");
    private static final int MAX_TEXT_LENGTH = 500;

    private BookValidator() {
    }

    /**
     * Validates the request and returns a copy with trimmed text fields.
     *
     * @throws ValidationException listing every problem found
     */
    public static BookRequest validate(BookRequest request) {
        List<String> errors = new ArrayList<>();
        if (request == null) {
            throw new ValidationException(List.of("request body is required"));
        }

        String title = trimToNull(request.title());
        String author = trimToNull(request.author());
        String isbn = trimToNull(request.isbn());

        if (title == null) {
            errors.add("title is required");
        } else if (title.length() > MAX_TEXT_LENGTH) {
            errors.add("title must be at most " + MAX_TEXT_LENGTH + " characters");
        }

        if (author == null) {
            errors.add("author is required");
        } else if (author.length() > MAX_TEXT_LENGTH) {
            errors.add("author must be at most " + MAX_TEXT_LENGTH + " characters");
        }

        Integer year = request.year();
        if (year != null && (year < 1 || year > Year.now().getValue() + 1)) {
            errors.add("year must be between 1 and " + (Year.now().getValue() + 1));
        }

        if (isbn != null && !isValidIsbn(isbn)) {
            errors.add("isbn must be a valid ISBN-10 or ISBN-13");
        }

        if (!errors.isEmpty()) {
            throw new ValidationException(errors);
        }
        return new BookRequest(title, author, year, isbn);
    }

    static boolean isValidIsbn(String isbn) {
        if (!ISBN_CHARS.matcher(isbn).matches()) {
            return false;
        }
        String digits = isbn.replace("-", "");
        if (digits.length() == 10) {
            return isValidIsbn10(digits);
        }
        if (digits.length() == 13) {
            return isValidIsbn13(digits);
        }
        return false;
    }

    private static boolean isValidIsbn10(String s) {
        int sum = 0;
        for (int i = 0; i < 9; i++) {
            char c = s.charAt(i);
            if (!Character.isDigit(c)) {
                return false;
            }
            sum += (10 - i) * (c - '0');
        }
        char last = Character.toUpperCase(s.charAt(9));
        int check;
        if (last == 'X') {
            check = 10;
        } else if (Character.isDigit(last)) {
            check = last - '0';
        } else {
            return false;
        }
        sum += check;
        return sum % 11 == 0;
    }

    private static boolean isValidIsbn13(String s) {
        int sum = 0;
        for (int i = 0; i < 13; i++) {
            char c = s.charAt(i);
            if (!Character.isDigit(c)) {
                return false;
            }
            sum += (c - '0') * (i % 2 == 0 ? 1 : 3);
        }
        return sum % 10 == 0;
    }

    private static String trimToNull(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }

    /**
     * Thrown when request data fails validation.
     */
    public static final class ValidationException extends RuntimeException {
        private final List<String> errors;

        public ValidationException(List<String> errors) {
            super(String.join("; ", errors));
            this.errors = List.copyOf(errors);
        }

        public List<String> errors() {
            return errors;
        }
    }
}
