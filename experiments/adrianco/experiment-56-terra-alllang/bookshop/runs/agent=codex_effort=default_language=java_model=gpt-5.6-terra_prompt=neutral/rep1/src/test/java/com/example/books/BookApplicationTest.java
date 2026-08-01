package com.example.books;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class BookApplicationTest {
    private BookRepository repository;

    @BeforeEach void openDatabase() throws Exception {
        Path db = Files.createTempFile("books-test", ".db");
        repository = new BookRepository("jdbc:sqlite:" + db);
    }

    @AfterEach void closeDatabase() throws Exception { repository.close(); }

    @Test void createsAndRetrievesBook() throws Exception {
        Book created = repository.create(new BookRequest("Dune", "Frank Herbert", 1965, "9780441172719"));

        assertEquals(1L, created.id());
        assertEquals("Dune", repository.findById(created.id()).orElseThrow().title());
        assertEquals(1965, repository.findById(created.id()).orElseThrow().year());
    }

    @Test void filtersBooksByExactAuthor() throws Exception {
        repository.create(new BookRequest("Dune", "Frank Herbert", null, null));
        repository.create(new BookRequest("Foundation", "Isaac Asimov", null, null));

        List<Book> books = repository.findAll("Frank Herbert");
        assertEquals(1, books.size());
        assertEquals("Dune", books.getFirst().title());
    }

    @Test void updatesAndDeletesBook() throws Exception {
        Book created = repository.create(new BookRequest("Old Title", "Writer", null, null));

        Book updated = repository.update(created.id(), new BookRequest("New Title", "Writer", 2020, "x")).orElseThrow();
        assertEquals("New Title", updated.title());
        assertTrue(repository.delete(created.id()));
        assertTrue(repository.findById(created.id()).isEmpty());
        assertFalse(repository.delete(created.id()));
    }

    @Test void rejectsMissingRequiredFields() {
        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class,
                () -> BookApplication.valid(new BookRequest(" ", "", null, null)));
        assertEquals("title and author are required", exception.getMessage());
    }
}
