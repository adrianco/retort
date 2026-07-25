package com.bookapi.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public class BookRequest {
    @NotBlank(message = "Title is required")
    @Size(max = 255, message = "Title must be less than 255 characters")
    private String title;

    @NotBlank(message = "Author is required")
    @Size(max = 255, message = "Author must be less than 255 characters")
    private String author;

    private Integer year;

    @Size(max = 20, message = "ISBN must be less than 20 characters")
    private String isbn;

    // Constructors
    public BookRequest() {}

    public BookRequest(String title, String author, Integer year, String isbn) {
        this.title = title;
        this.author = author;
        this.year = year;
        this.isbn = isbn;
    }

    // Getters
    public String getTitle() { return title; }
    public String getAuthor() { return author; }
    public Integer getYear() { return year; }
    public String getIsbn() { return isbn; }

    // Setters
    public void setTitle(String title) { this.title = title; }
    public void setAuthor(String author) { this.author = author; }
    public void setYear(Integer year) { this.year = year; }
    public void setIsbn(String isbn) { this.isbn = isbn; }
}
