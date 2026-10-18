package com.example.books;

/**
 * A book as stored and returned by the API.
 *
 * @param id     database identifier
 * @param title  required title
 * @param author required author
 * @param year   publication year (optional)
 * @param isbn   ISBN (optional)
 */
public record Book(long id, String title, String author, Integer year, String isbn) {
}
