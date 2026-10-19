package com.example.bookapi;

/**
 * A book in the collection.
 *
 * @param id     database-assigned identifier
 * @param title  book title (required)
 * @param author book author (required)
 * @param year   publication year (optional)
 * @param isbn   ISBN (optional)
 */
public record Book(Long id, String title, String author, Integer year, String isbn) {
}
