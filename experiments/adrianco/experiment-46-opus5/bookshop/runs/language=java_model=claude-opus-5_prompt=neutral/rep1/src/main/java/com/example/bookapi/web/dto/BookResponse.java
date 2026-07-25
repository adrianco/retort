package com.example.bookapi.web.dto;

import com.example.bookapi.model.Book;

import java.time.Instant;

/** JSON representation of a book returned to clients. */
public record BookResponse(
        Long id,
        String title,
        String author,
        Integer year,
        String isbn,
        Instant createdAt,
        Instant updatedAt) {

    public static BookResponse from(Book book) {
        return new BookResponse(
                book.id(),
                book.title(),
                book.author(),
                book.year(),
                book.isbn(),
                book.createdAt(),
                book.updatedAt());
    }
}
