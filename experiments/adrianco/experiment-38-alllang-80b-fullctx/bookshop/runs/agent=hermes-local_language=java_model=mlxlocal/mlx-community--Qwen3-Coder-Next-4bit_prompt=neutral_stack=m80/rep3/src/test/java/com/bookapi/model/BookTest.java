package com.bookapi.model;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class BookTest {

    @Test
    public void testBookConstructorWithId() {
        Book book = new Book(1, "The Great Gatsby", "F. Scott Fitzgerald", 1925, "978-0743273565");
        
        assertEquals(1, book.getId());
        assertEquals("The Great Gatsby", book.getTitle());
        assertEquals("F. Scott Fitzgerald", book.getAuthor());
        assertEquals(1925, book.getYear());
        assertEquals("978-0743273565", book.getIsbn());
    }

    @Test
    public void testBookConstructorWithoutId() {
        Book book = new Book("1984", "George Orwell", 1949, "978-0451524935");
        
        assertNull(book.getId());
        assertEquals("1984", book.getTitle());
        assertEquals("George Orwell", book.getAuthor());
        assertEquals(1949, book.getYear());
        assertEquals("978-0451524935", book.getIsbn());
    }

    @Test
    public void testSetters() {
        Book book = new Book();
        book.setId(1);
        book.setTitle("Test Book");
        book.setAuthor("Test Author");
        book.setYear(2024);
        book.setIsbn("123-456");
        
        assertEquals(1, book.getId());
        assertEquals("Test Book", book.getTitle());
        assertEquals("Test Author", book.getAuthor());
        assertEquals(2024, book.getYear());
        assertEquals("123-456", book.getIsbn());
    }

    @Test
    public void testEqualsAndHashCode() {
        Book book1 = new Book(1, "Book Title", "Author Name", 2024, "ISBN123");
        Book book2 = new Book(1, "Book Title", "Author Name", 2024, "ISBN123");
        Book book3 = new Book(2, "Different Book", "Different Author", 2023, "ISBN456");
        
        assertEquals(book1, book2);
        assertEquals(book1.hashCode(), book2.hashCode());
        assertNotEquals(book1, book3);
        assertNotEquals(book1.hashCode(), book3.hashCode());
    }

    @Test
    public void testToString() {
        Book book = new Book(1, "Test Book", "Test Author", 2024, "ISBN123");
        String toString = book.toString();
        
        assertTrue(toString.contains("id=1"));
        assertTrue(toString.contains("Test Book"));
        assertTrue(toString.contains("Test Author"));
        assertTrue(toString.contains("2024"));
        assertTrue(toString.contains("ISBN123"));
    }
}
