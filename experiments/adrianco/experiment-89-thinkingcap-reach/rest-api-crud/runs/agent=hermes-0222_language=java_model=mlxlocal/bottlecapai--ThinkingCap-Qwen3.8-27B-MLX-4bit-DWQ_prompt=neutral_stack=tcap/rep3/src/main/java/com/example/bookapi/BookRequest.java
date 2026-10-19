package com.example.bookapi;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

/**
 * JSON payload for creating or updating a book.
 * Title and author are required; year and isbn are optional.
 * Unknown JSON properties are ignored.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record BookRequest(String title, String author, Integer year, String isbn) {
}
