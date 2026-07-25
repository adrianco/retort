package com.bookapi.dto;

public class BookResponse {
    private Long id;
    private String title;
    private String author;
    private Integer year;
    private String isbn;

    // Constructors
    public BookResponse() {}

    public BookResponse(Long id, String title, String author, Integer year, String isbn) {
        this.id = id;
        this.title = title;
        this.author = author;
        this.year = year;
        this.isbn = isbn;
    }

    // Getters
    public Long getId() { return id; }
    public String getTitle() { return title; }
    public String getAuthor() { return author; }
    public Integer getYear() { return year; }
    public String getIsbn() { return isbn; }

    // Setters
    public void setId(Long id) { this.id = id; }
    public void setTitle(String title) { this.title = title; }
    public void setAuthor(String author) { this.author = author; }
    public void setYear(Integer year) { this.year = year; }
    public void setIsbn(String isbn) { this.isbn = isbn; }
}
