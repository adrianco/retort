package com.bookapi.repository;

import com.bookapi.model.Book;
import org.junit.jupiter.api.*;

import java.io.File;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.Statement;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;

public class BookRepositoryTest {
    
    private BookRepository repository;
    private File tempDb;

    @BeforeEach
    void setup() throws Exception {
        // Create a temporary database file
        tempDb = File.createTempFile("test-books", ".db");
        tempDb.deleteOnExit();
        
        // Create fresh database with proper initialization
        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + tempDb.getAbsolutePath())) {
            Statement stmt = conn.createStatement();
            stmt.execute(
                "CREATE TABLE IF NOT EXISTS books (" +
                "id INTEGER PRIMARY KEY AUTOINCREMENT, " +
                "title TEXT NOT NULL, " +
                "author TEXT NOT NULL, " +
                "year INTEGER NOT NULL, " +
                "isbn TEXT)"
            );
        }
        
        // Create repository with temp db path
        repository = new BookRepository("jdbc:sqlite:" + tempDb.getAbsolutePath());
    }

    @AfterEach
    void teardown() {
        if (tempDb != null && tempDb.exists()) {
            tempDb.delete();
        }
    }

    @Test
    void testFindById() {
        // Given
        Book book = new Book("Test Book", "Test Author", 2024, "ISBN123");
        Book savedBook = repository.save(book);
        
        // When
        Optional<Book> found = repository.findById(savedBook.getId());
        
        // Then
        assertTrue(found.isPresent());
        assertEquals(savedBook.getId(), found.get().getId());
        assertEquals("Test Book", found.get().getTitle());
    }

    @Test
    void testFindByIdNotFound() {
        // When
        Optional<Book> found = repository.findById(999);
        
        // Then
        assertFalse(found.isPresent());
    }

    @Test
    void testFindAll() {
        // Given
        repository.save(new Book("Book 1", "Author A", 2020, "ISBN1"));
        repository.save(new Book("Book 2", "Author B", 2021, "ISBN2"));
        repository.save(new Book("Book 3", "Author A", 2022, "ISBN3"));
        
        // When
        List<Book> books = repository.findAll(null);
        
        // Then
        assertEquals(3, books.size());
    }

    @Test
    void testFindAllWithAuthorFilter() {
        // Given
        repository.save(new Book("Book 1", "Author A", 2020, "ISBN1"));
        repository.save(new Book("Book 2", "Author B", 2021, "ISBN2"));
        repository.save(new Book("Book 3", "Author A", 2022, "ISBN3"));
        
        // When
        List<Book> books = repository.findAll("Author A");
        
        // Then
        assertEquals(2, books.size());
        assertTrue(books.stream().allMatch(b -> b.getAuthor().equals("Author A")));
    }

    @Test
    void testSaveNewBook() {
        // Given
        Book book = new Book("New Book", "New Author", 2024, "ISBN999");
        
        // When
        Book saved = repository.save(book);
        
        // Then
        assertNotNull(saved);
        assertNotNull(saved.getId());
        assertEquals("New Book", saved.getTitle());
    }

    @Test
    void testSaveExistingBook() {
        // Given
        Book book = repository.save(new Book("Original", "Original Author", 2020, "ISBN1"));
        int id = book.getId();
        
        // When
        book.setTitle("Updated Title");
        book.setAuthor("Updated Author");
        Book updated = repository.save(book);
        
        // Then
        assertNotNull(updated);
        assertEquals(id, updated.getId());
        assertEquals("Updated Title", updated.getTitle());
        assertEquals("Updated Author", updated.getAuthor());
    }

    @Test
    void testDelete() {
        // Given
        Book book = repository.save(new Book("To Delete", "Author", 2024, "ISBN1"));
        int id = book.getId();
        
        // When
        boolean deleted = repository.delete(id);
        
        // Then
        assertTrue(deleted);
        assertFalse(repository.findById(id).isPresent());
    }

    @Test
    void testDeleteNotFound() {
        // When
        boolean deleted = repository.delete(999);
        
        // Then
        assertFalse(deleted);
    }
}
