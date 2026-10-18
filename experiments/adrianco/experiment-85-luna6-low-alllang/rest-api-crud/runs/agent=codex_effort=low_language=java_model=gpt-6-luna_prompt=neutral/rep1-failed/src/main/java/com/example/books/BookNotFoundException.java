package com.example.books;

public class BookNotFoundException extends RuntimeException {
    public BookNotFoundException(long id) { super("Book with id " + id + " was not found"); }
}
