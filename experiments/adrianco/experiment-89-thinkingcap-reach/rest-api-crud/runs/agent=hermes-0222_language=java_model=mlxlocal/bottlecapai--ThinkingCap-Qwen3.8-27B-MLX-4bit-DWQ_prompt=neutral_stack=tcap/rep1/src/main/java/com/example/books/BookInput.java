package com.example.books;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

/**
 * Client-supplied book payload for create/update requests.
 * Unknown JSON fields are ignored; {@code year} and {@code isbn} are optional.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record BookInput(String title, String author, Integer year, String isbn) {
}
