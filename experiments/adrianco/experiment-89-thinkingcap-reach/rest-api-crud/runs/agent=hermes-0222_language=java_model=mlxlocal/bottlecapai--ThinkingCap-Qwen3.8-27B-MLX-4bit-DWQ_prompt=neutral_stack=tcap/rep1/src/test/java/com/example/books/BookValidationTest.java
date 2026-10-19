package com.example.books;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Unit tests for input validation and JSON body parsing.
 */
class BookValidationTest {

    @Test
    void rejectsMissingTitle() {
        BookException ex = assertThrows(BookException.class,
                () -> BookValidation.validate(new BookInput(null, "Author", null, null)));
        assertEquals(400, ex.status());
        assertTrue(ex.getMessage().contains("title"));
    }

    @Test
    void rejectsBlankTitle() {
        BookException ex = assertThrows(BookException.class,
                () -> BookValidation.validate(new BookInput("   ", "Author", null, null)));
        assertEquals(400, ex.status());
    }

    @Test
    void rejectsMissingAuthor() {
        BookException ex = assertThrows(BookException.class,
                () -> BookValidation.validate(new BookInput("Title", "", null, null)));
        assertEquals(400, ex.status());
        assertTrue(ex.getMessage().contains("author"));
    }

    @Test
    void acceptsValidInputAndTrimsFields() {
        BookInput in = BookValidation.validate(new BookInput("  Dune  ", "  Frank Herbert  ", 1965, "978-0441172719"));
        assertEquals("Dune", in.title());
        assertEquals("Frank Herbert", in.author());
        assertEquals(1965, in.year());
        assertEquals("978-0441172719", in.isbn());
    }

    @Test
    void acceptsInputWithoutOptionalFields() {
        BookInput in = BookValidation.validate(new BookInput("Title", "Author", null, null));
        assertEquals(null, in.year());
        assertEquals(null, in.isbn());
    }

    @Test
    void malformedJsonBodyThrows400() {
        BookException ex = assertThrows(BookException.class,
                () -> Json.readBookInput("{not json".getBytes(java.nio.charset.StandardCharsets.UTF_8)));
        assertEquals(400, ex.status());
    }

    @Test
    void emptyBodyThrows400() {
        BookException ex = assertThrows(BookException.class,
                () -> Json.readBookInput(new byte[0]));
        assertEquals(400, ex.status());
    }

    @Test
    void unknownJsonFieldsAreIgnored() {
        BookInput in = Json.readBookInput(
                "{\"title\":\"T\",\"author\":\"A\",\"genre\":\"sci-fi\"}".getBytes(java.nio.charset.StandardCharsets.UTF_8));
        assertEquals("T", in.title());
        assertEquals("A", in.author());
    }

    @Test
    void nonNumericYearIsRejectedAsInvalidJson() {
        BookException ex = assertThrows(BookException.class,
                () -> Json.readBookInput("{\"title\":\"T\",\"author\":\"A\",\"year\":\"abc\"}".getBytes(java.nio.charset.StandardCharsets.UTF_8)));
        assertEquals(400, ex.status());
    }
}
