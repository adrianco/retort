package com.example.books;

/** A book in the collection. {@code id} is null until the book is persisted. */
public record Book(Long id, String title, String author, Integer year, String isbn) {
}
