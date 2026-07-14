package com.example.books;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import java.util.Map;
import java.util.Optional;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class BookServiceTest {

    private BookRepository repository;
    private BookService service;

    @BeforeEach
    void setUp() {
        repository = new BookRepository("jdbc:sqlite::memory:");
        service = new BookService(repository);
    }

    @AfterEach
    void tearDown() {
        repository.close();
    }

    @Test
    void createPersistsAndAssignsId() {
        Book book = service.create(Map.of("title", "Dune", "author", "Herbert", "year", 1965.0));
        assertTrue(book.getId() > 0);
        assertEquals("Dune", book.getTitle());
        assertEquals(Integer.valueOf(1965), book.getYear());
    }

    @Test
    void createTrimsRequiredFields() {
        Book book = service.create(Map.of("title", "  Dune  ", "author", "  Herbert  "));
        assertEquals("Dune", book.getTitle());
        assertEquals("Herbert", book.getAuthor());
        assertNull(book.getYear());
    }

    @Test
    void missingTitleIsRejected() {
        ValidationException ex = assertThrows(ValidationException.class,
            () -> service.create(Map.of("author", "Herbert")));
        assertTrue(ex.getMessage().contains("title"));
    }

    @Test
    void missingAuthorIsRejected() {
        ValidationException ex = assertThrows(ValidationException.class,
            () -> service.create(Map.of("title", "Dune")));
        assertTrue(ex.getMessage().contains("author"));
    }

    @Test
    void blankTitleIsRejected() {
        assertThrows(ValidationException.class,
            () -> service.create(Map.of("title", "   ", "author", "Herbert")));
    }

    @Test
    void nonIntegerYearIsRejected() {
        assertThrows(ValidationException.class,
            () -> service.create(Map.of("title", "Dune", "author", "Herbert", "year", 1965.5)));
    }

    @Test
    void listFiltersByAuthor() {
        service.create(Map.of("title", "Dune", "author", "Herbert"));
        service.create(Map.of("title", "Hyperion", "author", "Simmons"));

        List<Book> all = service.list(null);
        assertEquals(2, all.size());

        List<Book> filtered = service.list("Herbert");
        assertEquals(1, filtered.size());
        assertEquals("Dune", filtered.get(0).getTitle());
    }

    @Test
    void updateChangesExistingBook() {
        Book created = service.create(Map.of("title", "Dune", "author", "Herbert"));
        Optional<Book> updated = service.update(created.getId(),
            Map.of("title", "Dune Messiah", "author", "Frank Herbert"));
        assertTrue(updated.isPresent());
        assertEquals("Dune Messiah", updated.get().getTitle());

        Optional<Book> reloaded = service.get(created.getId());
        assertEquals("Frank Herbert", reloaded.get().getAuthor());
    }

    @Test
    void updateMissingReturnsEmpty() {
        Optional<Book> updated = service.update(12345,
            Map.of("title", "X", "author", "Y"));
        assertFalse(updated.isPresent());
    }

    @Test
    void deleteRemovesBook() {
        Book created = service.create(Map.of("title", "Dune", "author", "Herbert"));
        assertTrue(service.delete(created.getId()));
        assertFalse(service.get(created.getId()).isPresent());
        assertFalse(service.delete(created.getId()));
    }
}
