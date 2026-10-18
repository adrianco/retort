package com.example.books;

/**
 * A book as stored and returned by the API.
 *
 * @param id     database identifier
 * @param title  required, non-blank
 * @param author required, non-blank
 * @param year   optional publication year
 * @param isbn   optional ISBN-10 or ISBN-13
 */
public record Book(Long id, String title, String author, Integer year, String isbn) {
}
