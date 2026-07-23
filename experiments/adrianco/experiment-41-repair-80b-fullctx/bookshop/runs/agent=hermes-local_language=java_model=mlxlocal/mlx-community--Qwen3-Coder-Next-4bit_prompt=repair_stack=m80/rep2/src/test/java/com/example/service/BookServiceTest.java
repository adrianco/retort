package com.example.service;

import com.example.model.Book;
import com.example.repository.BookRepository;
import org.junit.jupiter.api.*;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;

public class BookServiceTest {
    private BookService bookService;
    private BookRepository mockRepository;

    @BeforeEach
    void setUp() {
        // Use a simple in-memory mock implementation
        mockRepository = new InMemoryBookRepository();
        bookService = new BookService(mockRepository);
    }

    @AfterEach
    void tearDown() {
        if (mockRepository instanceof InMemoryBookRepository) {
            ((InMemoryBookRepository) mockRepository).clear();
        }
    }

    @Test
    void testCreateBook_Success() {
        Book book = new Book("Test Book", "Test Author", 2024, "1234567890");

        Book result = bookService.createBook(book);

        assertNotNull(result);
        assertNotNull(result.getId());
        assertEquals("Test Book", result.getTitle());
        assertEquals("Test Author", result.getAuthor());
    }

    @Test
    void testCreateBook_ValidationFail_TitleEmpty() {
        Book book = new Book("", "Test Author", 2024, "1234567890");

        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () -> {
            bookService.createBook(book);
        });

        assertEquals("Title is required", exception.getMessage());
    }

    @Test
    void testCreateBook_ValidationFail_AuthorEmpty() {
        Book book = new Book("Test Book", "", 2024, "1234567890");

        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () -> {
            bookService.createBook(book);
        });

        assertEquals("Author is required", exception.getMessage());
    }

    @Test
    void testGetBookById_Success() {
        Book book = new Book("Test Book", "Test Author", 2024, "1234567890");
        Book saved = bookService.createBook(book);

        Optional<Book> result = bookService.getBookById(saved.getId());

        assertTrue(result.isPresent());
        assertEquals("Test Book", result.get().getTitle());
    }

    @Test
    void testGetBookById_NotFound() {
        Optional<Book> result = bookService.getBookById(999L);

        assertFalse(result.isPresent());
    }

    @Test
    void testGetAllBooks() {
        Book book1 = new Book("Book 1", "Author 1", 2024, "111");
        Book book2 = new Book("Book 2", "Author 2", 2023, "222");

        bookService.createBook(book1);
        bookService.createBook(book2);

        java.util.List<Book> result = bookService.getAllBooks();

        assertEquals(2, result.size());
        assertEquals("Book 1", result.get(0).getTitle());
        assertEquals("Book 2", result.get(1).getTitle());
    }

    @Test
    void testFindBooksByAuthor() {
        Book book1 = new Book("Book 1", "Author A", 2024, "111");
        Book book2 = new Book("Book 2", "Author B", 2023, "222");
        Book book3 = new Book("Book 3", "Author A", 2022, "333");

        bookService.createBook(book1);
        bookService.createBook(book2);
        bookService.createBook(book3);

        java.util.List<Book> result = bookService.findBooksByAuthor("Author A");

        assertEquals(2, result.size());
        assertEquals("Author A", result.get(0).getAuthor());
        assertEquals("Author A", result.get(1).getAuthor());
    }

    @Test
    void testUpdateBook_Success() {
        Book book = bookService.createBook(new Book("Original Title", "Original Author", 2024, "123"));

        Book updated = new Book(book.getId(), "Updated Title", "Updated Author", 2025, "999");

        Optional<Book> result = bookService.updateBook(updated);

        assertTrue(result.isPresent());
        assertEquals("Updated Title", result.get().getTitle());
        assertEquals("Updated Author", result.get().getAuthor());
        assertEquals(Integer.valueOf(2025), result.get().getYear());
    }

    @Test
    void testUpdateBook_ValidationFail_TitleEmpty() {
        Book book = new Book(1L, "", "Updated Author", 2025, "9999999999");

        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () -> {
            bookService.updateBook(book);
        });

        assertEquals("Title is required", exception.getMessage());
    }

    @Test
    void testDeleteBook_Success() {
        Book book = bookService.createBook(new Book("To Delete", "Author", 2024, "123"));

        boolean result = bookService.deleteBook(book.getId());

        assertTrue(result);
        assertFalse(bookService.getBookById(book.getId()).isPresent());
    }

    @Test
    void testDeleteBook_NotFound() {
        boolean result = bookService.deleteBook(999L);

        assertFalse(result);
    }

    // Simple in-memory mock for testing
    private static class InMemoryBookRepository extends BookRepository {
        private final java.util.Map<Long, Book> store = new java.util.HashMap<>();
        private long nextId = 1;

        public InMemoryBookRepository() {
            super();
        }

        public void clear() {
            store.clear();
            nextId = 1;
        }

        @Override
        public Book save(Book book) {
            if (book.getId() == null) {
                book.setId(nextId++);
                store.put(book.getId(), book);
            } else {
                store.put(book.getId(), book);
            }
            return book;
        }

        @Override
        public Optional<Book> findById(Long id) {
            return Optional.ofNullable(store.get(id));
        }

        @Override
        public java.util.List<Book> findAll() {
            return new java.util.ArrayList<>(store.values());
        }

        @Override
        public java.util.List<Book> findByAuthor(String author) {
            return store.values().stream()
                    .filter(b -> b.getAuthor().equals(author))
                    .collect(java.util.stream.Collectors.toList());
        }

        @Override
        public boolean delete(Long id) {
            return store.remove(id) != null;
        }

        @Override
        public void init() {
            // Skip DB initialization for in-memory
        }

        @Override
        public void close() {
            // Skip DB close for in-memory
        }
    }
}
