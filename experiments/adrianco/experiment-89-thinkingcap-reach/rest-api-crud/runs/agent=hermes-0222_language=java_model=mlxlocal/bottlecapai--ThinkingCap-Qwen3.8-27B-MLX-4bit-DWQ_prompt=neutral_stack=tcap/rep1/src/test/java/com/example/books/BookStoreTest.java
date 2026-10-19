package com.example.books;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.sql.SQLException;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Unit tests for the SQLite-backed {@link BookStore}.
 */
class BookStoreTest {

    private BookStore store;

    @BeforeEach
    void setUp() throws Exception {
        String db = Files.createTempDirectory("bookstore-test").resolve("test.db").toString();
        store = new BookStore("jdbc:sqlite:" + db);
    }

    @AfterEach
    void tearDown() throws SQLException {
        store.close();
    }

    @Test
    void createAssignsIdAndPersistsAllFields() {
        Book book = store.create("Dune", "Frank Herbert", 1965, "978-0441172719");
        assertTrue(book.id() > 0);
        assertEquals("Dune", book.title());
        assertEquals("Frank Herbert", book.author());
        assertEquals(1965, book.year());
        assertEquals("978-0441172719", book.isbn());

        Book fetched = store.get(book.id()).orElseThrow();
        assertEquals(book, fetched);
    }

    @Test
    void createSupportsNullOptionalFields() {
        Book book = store.create("Moby-Dick", "Melville", null, null);
        Book fetched = store.get(book.id()).orElseThrow();
        assertEquals(null, fetched.year());
        assertEquals(null, fetched.isbn());
    }

    @Test
    void listReturnsAllBooksOrderedById() {
        Book a = store.create("A", "Alpha", null, null);
        Book b = store.create("B", "Beta", null, null);
        List<Book> all = store.list(null);
        assertEquals(2, all.size());
        assertEquals(a.id(), all.get(0).id());
        assertEquals(b.id(), all.get(1).id());
    }

    @Test
    void listFiltersByAuthor() {
        store.create("A1", "Alpha", null, null);
        store.create("B1", "Beta", null, null);
        store.create("A2", "Alpha", null, null);
        List<Book> alpha = store.list("Alpha");
        assertEquals(2, alpha.size());
        assertTrue(alpha.stream().allMatch(b -> b.author().equals("Alpha")));
        assertTrue(store.list("Gamma").isEmpty());
    }

    @Test
    void getReturnsEmptyForMissingId() {
        assertTrue(store.get(424242).isEmpty());
    }

    @Test
    void updateReplacesRequiredAndKeepsOmittedOptionals() {
        Book book = store.create("Old", "Writer", 1999, "111");
        Book updated = store.update(book.id(), "New", "Editor", null, null);
        assertEquals("New", updated.title());
        assertEquals("Editor", updated.author());
        assertEquals(1999, updated.year());
        assertEquals("111", updated.isbn());

        Book fetched = store.get(book.id()).orElseThrow();
        assertEquals("New", fetched.title());
        assertEquals("Editor", fetched.author());
        assertEquals(1999, fetched.year());
        assertEquals("111", fetched.isbn());
    }

    @Test
    void updateReplacesProvidedOptionals() {
        Book book = store.create("Old", "Writer", 1999, "111");
        Book updated = store.update(book.id(), "New", "Editor", 2001, "222");
        assertEquals(2001, updated.year());
        assertEquals("222", updated.isbn());
    }

    @Test
    void updateMissingBookThrows404() {
        BookException ex = assertThrows(BookException.class,
                () -> store.update(99999, "T", "A", null, null));
        assertEquals(404, ex.status());
    }

    @Test
    void deleteRemovesBookAndReportsFalseWhenMissing() {
        Book book = store.create("Temp", "Ghost", null, null);
        assertTrue(store.delete(book.id()));
        assertTrue(store.get(book.id()).isEmpty());
        assertFalse(store.delete(book.id()));
    }
}
