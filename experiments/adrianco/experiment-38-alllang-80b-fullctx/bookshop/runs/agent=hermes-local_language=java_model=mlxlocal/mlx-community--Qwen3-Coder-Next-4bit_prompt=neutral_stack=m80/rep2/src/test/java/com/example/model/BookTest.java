package com.example.model;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

public class BookTest {

    @Test
    void testBookConstructorWithId() {
        Book book = new Book(1L, "Test Book", "Test Author", 2024, "1234567890");

        assertEquals(1L, book.getId());
        assertEquals("Test Book", book.getTitle());
        assertEquals("Test Author", book.getAuthor());
        assertEquals(Integer.valueOf(2024), book.getYear());
        assertEquals("1234567890", book.getIsbn());
    }

    @Test
    void testBookConstructorWithoutId() {
        Book book = new Book("Test Book", "Test Author", 2024, "1234567890");

        assertNull(book.getId());
        assertEquals("Test Book", book.getTitle());
        assertEquals("Test Author", book.getAuthor());
        assertEquals(Integer.valueOf(2024), book.getYear());
        assertEquals("1234567890", book.getIsbn());
    }

    @Test
    void testSetters() {
        Book book = new Book();
        book.setId(1L);
        book.setTitle("New Title");
        book.setAuthor("New Author");
        book.setYear(2025);
        book.setIsbn("9999999999");

        assertEquals(1L, book.getId());
        assertEquals("New Title", book.getTitle());
        assertEquals("New Author", book.getAuthor());
        assertEquals(Integer.valueOf(2025), book.getYear());
        assertEquals("9999999999", book.getIsbn());
    }

    @Test
    void testEqualsAndHashCode() {
        Book book1 = new Book(1L, "Book", "Author", 2024, "123");
        Book book2 = new Book(1L, "Book", "Author", 2024, "123");
        Book book3 = new Book(2L, "Different", "Author", 2024, "456");

        assertEquals(book1, book2);
        assertEquals(book1.hashCode(), book2.hashCode());
        assertNotEquals(book1, book3);
        assertNotEquals(book1.hashCode(), book3.hashCode());
    }

    @Test
    void testEqualsWithNull() {
        Book book = new Book(1L, "Book", "Author", 2024, "123");
        assertNotEquals(null, book);
    }

    @Test
    void testEqualsWithDifferentClass() {
        Book book = new Book(1L, "Book", "Author", 2024, "123");
        assertNotEquals(book, "Not a Book");
    }

    @Test
    void testToString() {
        Book book = new Book(1L, "Book Title", "Book Author", 2024, "123");
        String toString = book.toString();

        assertTrue(toString.contains("Book Title"));
        assertTrue(toString.contains("Book Author"));
        assertTrue(toString.contains("1"));
        assertTrue(toString.contains("2024"));
        assertTrue(toString.contains("123"));
    }
}
