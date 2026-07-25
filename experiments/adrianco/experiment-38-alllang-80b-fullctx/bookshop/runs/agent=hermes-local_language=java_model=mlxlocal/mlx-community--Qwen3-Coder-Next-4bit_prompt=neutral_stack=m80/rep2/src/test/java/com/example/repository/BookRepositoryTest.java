package com.example.repository;

import com.example.model.Book;
import org.junit.jupiter.api.*;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;

public class BookRepositoryTest {
    private BookRepository repository;

    @BeforeEach
    void setUp() {
        repository = new InMemoryBookRepository();
    }

    @AfterEach
    void tearDown() {
        if (repository instanceof InMemoryBookRepository) {
            ((InMemoryBookRepository) repository).clear();
        }
    }

    @Test
    void testSaveAndFindById() {
        Book book = new Book("Test Book", "Test Author", 2024, "1234567890");
        Book saved = repository.save(book);

        assertNotNull(saved.getId());
        assertEquals("Test Book", saved.getTitle());
        assertEquals("Test Author", saved.getAuthor());

        Optional<Book> found = repository.findById(saved.getId());
        assertTrue(found.isPresent());
        assertEquals(saved.getId(), found.get().getId());
        assertEquals(saved.getTitle(), found.get().getTitle());
    }

    @Test
    void testFindAll() {
        Book book1 = new Book("Book 1", "Author A", 2024, "111");
        Book book2 = new Book("Book 2", "Author B", 2023, "222");

        repository.save(book1);
        repository.save(book2);

        List<Book> all = repository.findAll();
        assertEquals(2, all.size());
        assertEquals("Book 1", all.get(0).getTitle());
        assertEquals("Book 2", all.get(1).getTitle());
    }

    @Test
    void testFindByAuthor() {
        Book book1 = new Book("Book 1", "Author A", 2024, "111");
        Book book2 = new Book("Book 2", "Author B", 2023, "222");
        Book book3 = new Book("Book 3", "Author A", 2022, "333");

        repository.save(book1);
        repository.save(book2);
        repository.save(book3);

        List<Book> byAuthorA = repository.findByAuthor("Author A");
        assertEquals(2, byAuthorA.size());
        assertEquals("Author A", byAuthorA.get(0).getAuthor());
        assertEquals("Author A", byAuthorA.get(1).getAuthor());
    }

    @Test
    void testUpdate() {
        Book book = repository.save(new Book("Original Title", "Original Author", 2024, "123"));
        Long id = book.getId();

        book.setTitle("Updated Title");
        book.setAuthor("Updated Author");
        book.setYear(2025);
        book.setIsbn("999");

        Book updated = repository.save(book);

        assertEquals(id, updated.getId());
        assertEquals("Updated Title", updated.getTitle());
        assertEquals("Updated Author", updated.getAuthor());
        assertEquals(Integer.valueOf(2025), updated.getYear());
        assertEquals("999", updated.getIsbn());

        Optional<Book> found = repository.findById(id);
        assertTrue(found.isPresent());
        assertEquals("Updated Title", found.get().getTitle());
    }

    @Test
    void testDelete() {
        Book book = repository.save(new Book("To Delete", "Author", 2024, "123"));
        Long id = book.getId();

        boolean deleted = repository.delete(id);
        assertTrue(deleted);

        Optional<Book> found = repository.findById(id);
        assertFalse(found.isPresent());

        boolean deletedAgain = repository.delete(id);
        assertFalse(deletedAgain);
    }

    @Test
    void testFindById_NotFound() {
        Optional<Book> found = repository.findById(999L);
        assertFalse(found.isPresent());
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
