package com.example.books;

/**
 * Client-supplied book data for create and update operations.
 * Fields are nullable so that validation can report missing values explicitly.
 */
public record BookRequest(String title, String author, Integer year, String isbn) {
}
