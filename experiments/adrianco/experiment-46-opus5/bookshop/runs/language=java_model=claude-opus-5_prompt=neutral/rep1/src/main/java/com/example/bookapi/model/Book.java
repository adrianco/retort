package com.example.bookapi.model;

import java.time.Instant;

/**
 * A book as stored in the database. {@code id}, {@code createdAt} and
 * {@code updatedAt} are server-assigned.
 */
public record Book(
        Long id,
        String title,
        String author,
        Integer year,
        String isbn,
        Instant createdAt,
        Instant updatedAt) {
}
