package com.example.books;

/**
 * A book in the collection. {@code id} is null until the book has been persisted.
 */
public record Book(Long id, String title, String author, Integer year, String isbn) {

    /** Returns a copy of this book with the given id. */
    public Book withId(long newId) {
        return new Book(newId, title, author, year, isbn);
    }
}
