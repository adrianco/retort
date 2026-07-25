package com.example.bookapi.web.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/**
 * Request body for creating and replacing books.
 *
 * <p>Title and author are required; year and isbn are optional. A supplied ISBN
 * must be a well-formed ISBN-10 or ISBN-13, optionally separated by hyphens or
 * spaces; it is normalised (separators stripped) before it is stored.
 */
public record BookRequest(

        @NotBlank(message = "title is required")
        @Size(max = 500, message = "title must be at most 500 characters")
        String title,

        @NotBlank(message = "author is required")
        @Size(max = 500, message = "author must be at most 500 characters")
        String author,

        @Min(value = 1, message = "year must be between 1 and 2200")
        @Max(value = 2200, message = "year must be between 1 and 2200")
        Integer year,

        @Pattern(
                regexp = "^(?:\\d[- ]?){9}[\\dXx]$|^(?:\\d[- ]?){12}\\d$",
                message = "isbn must be a valid ISBN-10 or ISBN-13")
        String isbn) {

    /** Blank strings are treated as "no ISBN supplied". */
    public BookRequest {
        if (isbn != null && isbn.isBlank()) {
            isbn = null;
        }
        if (title != null) {
            title = title.trim();
        }
        if (author != null) {
            author = author.trim();
        }
    }

    /** The ISBN with separators removed and any check digit upper-cased, or null. */
    public String normalisedIsbn() {
        return isbn == null ? null : isbn.replaceAll("[- ]", "").toUpperCase();
    }
}
