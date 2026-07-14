package com.example.books;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * A book in the collection.
 *
 * <p>{@code title} and {@code author} are required; {@code year} and {@code isbn}
 * are optional. {@code id} is assigned by the database.
 */
public final class Book {

    private long id;
    private String title;
    private String author;
    private Integer year;
    private String isbn;

    public Book() {
    }

    public Book(long id, String title, String author, Integer year, String isbn) {
        this.id = id;
        this.title = title;
        this.author = author;
        this.year = year;
        this.isbn = isbn;
    }

    public long getId() {
        return id;
    }

    public void setId(long id) {
        this.id = id;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getAuthor() {
        return author;
    }

    public void setAuthor(String author) {
        this.author = author;
    }

    public Integer getYear() {
        return year;
    }

    public void setYear(Integer year) {
        this.year = year;
    }

    public String getIsbn() {
        return isbn;
    }

    public void setIsbn(String isbn) {
        this.isbn = isbn;
    }

    /** Converts this book to a JSON-serializable map (preserving field order). */
    public Map<String, Object> toMap() {
        Map<String, Object> map = new LinkedHashMap<>();
        map.put("id", id);
        map.put("title", title);
        map.put("author", author);
        map.put("year", year);
        map.put("isbn", isbn);
        return map;
    }
}
