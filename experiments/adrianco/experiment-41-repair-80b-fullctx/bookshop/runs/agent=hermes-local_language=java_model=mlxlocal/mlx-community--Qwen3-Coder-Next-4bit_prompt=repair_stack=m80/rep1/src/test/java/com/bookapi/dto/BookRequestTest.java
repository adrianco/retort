package com.bookapi.dto;

import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;
import org.junit.jupiter.api.Test;

import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

public class BookRequestTest {

    private final ValidatorFactory factory = Validation.buildDefaultValidatorFactory();
    private final Validator validator = factory.getValidator();

    @Test
    public void testValidBookRequest() {
        BookRequest request = new BookRequest();
        request.setTitle("Clean Code");
        request.setAuthor("Robert C. Martin");
        request.setYear(2008);
        request.setIsbn("978-0132350884");

        Set<ConstraintViolation<BookRequest>> violations = validator.validate(request);
        assertTrue(violations.isEmpty(), "Valid book request should have no validation errors");
    }

    @Test
    public void testMissingTitle() {
        BookRequest request = new BookRequest();
        request.setAuthor("Robert C. Martin");
        request.setYear(2008);
        request.setIsbn("978-0132350884");

        Set<ConstraintViolation<BookRequest>> violations = validator.validate(request);
        assertEquals(1, violations.size(), "Missing title should produce one validation error");
        assertTrue(violations.stream()
                .anyMatch(v -> v.getMessage().equals("Title is required")));
    }

    @Test
    public void testMissingAuthor() {
        BookRequest request = new BookRequest();
        request.setTitle("Clean Code");
        request.setYear(2008);
        request.setIsbn("978-0132350884");

        Set<ConstraintViolation<BookRequest>> violations = validator.validate(request);
        assertEquals(1, violations.size(), "Missing author should produce one validation error");
        assertTrue(violations.stream()
                .anyMatch(v -> v.getMessage().equals("Author is required")));
    }

    @Test
    public void testTitleTooLong() {
        String longTitle = "a".repeat(256);
        BookRequest request = new BookRequest();
        request.setTitle(longTitle);
        request.setAuthor("Robert C. Martin");
        request.setYear(2008);
        request.setIsbn("978-0132350884");

        Set<ConstraintViolation<BookRequest>> violations = validator.validate(request);
        assertEquals(1, violations.size(), "Title too long should produce one validation error");
        assertTrue(violations.stream()
                .anyMatch(v -> v.getMessage().contains("less than 255 characters")));
    }

    @Test
    public void testAuthorTooLong() {
        String longAuthor = "a".repeat(256);
        BookRequest request = new BookRequest();
        request.setTitle("Clean Code");
        request.setAuthor(longAuthor);
        request.setYear(2008);
        request.setIsbn("978-0132350884");

        Set<ConstraintViolation<BookRequest>> violations = validator.validate(request);
        assertEquals(1, violations.size(), "Author too long should produce one validation error");
        assertTrue(violations.stream()
                .anyMatch(v -> v.getMessage().contains("less than 255 characters")));
    }

    @Test
    public void testIsbnTooLong() {
        String longIsbn = "a".repeat(21);
        BookRequest request = new BookRequest();
        request.setTitle("Clean Code");
        request.setAuthor("Robert C. Martin");
        request.setYear(2008);
        request.setIsbn(longIsbn);

        Set<ConstraintViolation<BookRequest>> violations = validator.validate(request);
        assertEquals(1, violations.size(), "ISBN too long should produce one validation error");
        assertTrue(violations.stream()
                .anyMatch(v -> v.getMessage().contains("less than 20 characters")));
    }
}
