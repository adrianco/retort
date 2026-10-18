package com.example.books;

import jakarta.validation.constraints.NotBlank;

public record BookRequest(
        @NotBlank(message = "title is required") String title,
        @NotBlank(message = "author is required") String author,
        Integer year,
        String isbn) { }
