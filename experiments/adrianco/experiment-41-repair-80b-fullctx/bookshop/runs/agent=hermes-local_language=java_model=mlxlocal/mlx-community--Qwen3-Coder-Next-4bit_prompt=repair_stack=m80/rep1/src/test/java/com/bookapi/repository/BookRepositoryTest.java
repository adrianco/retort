package com.bookapi.repository;

import com.bookapi.entity.Book;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@ActiveProfiles("test")
@Transactional
class BookRepositoryTest {

    @Autowired
    private BookRepository bookRepository;

    @BeforeEach
    void setUp() {
        bookRepository.deleteAll();
    }

    @Test
    void testSaveAndFindById() {
        Book book = new Book();
        book.setTitle("Clean Code");
        book.setAuthor("Robert C. Martin");
        book.setYear(2008);
        book.setIsbn("978-0132350884");

        Book saved = bookRepository.save(book);
        assertNotNull(saved.getId(), "Saved book should have an ID");
        assertEquals("Clean Code", saved.getTitle());
        assertEquals("Robert C. Martin", saved.getAuthor());

        Book found = bookRepository.findById(saved.getId()).orElse(null);
        assertNotNull(found, "Book should be found by ID");
        assertEquals(saved.getId(), found.getId());
    }

    @Test
    void testFindAll() {
        Book book1 = new Book();
        book1.setTitle("Clean Code");
        book1.setAuthor("Robert C. Martin");
        book1.setYear(2008);

        Book book2 = new Book();
        book2.setTitle("Design Patterns");
        book2.setAuthor("Gang of Four");
        book2.setYear(1994);

        bookRepository.saveAll(List.of(book1, book2));

        List<Book> allBooks = bookRepository.findAll();
        assertEquals(2, allBooks.size(), "Should find 2 books");
    }

    @Test
    void testFindByAuthor() {
        Book book1 = new Book();
        book1.setTitle("Clean Code");
        book1.setAuthor("Robert C. Martin");
        book1.setYear(2008);

        Book book2 = new Book();
        book2.setTitle("The Pragmatic Programmer");
        book2.setAuthor("David Thomas");
        book2.setYear(1999);

        Book book3 = new Book();
        book3.setTitle("Clean Architecture");
        book3.setAuthor("Robert C. Martin");
        book3.setYear(2017);

        bookRepository.saveAll(List.of(book1, book2, book3));

        List<Book> booksByAuthor = bookRepository.findByAuthor("Robert C. Martin");
        assertEquals(2, booksByAuthor.size(), "Should find 2 books by Robert C. Martin");
        assertTrue(booksByAuthor.stream()
                .allMatch(b -> b.getAuthor().equals("Robert C. Martin")));
    }

    @Test
    void testUpdateBook() {
        Book book = new Book();
        book.setTitle("Clean Code");
        book.setAuthor("Robert C. Martin");
        book.setYear(2008);
        book.setIsbn("978-0132350884");

        Book saved = bookRepository.save(book);

        saved.setTitle("Clean Code: A Handbook of Agile Software Craftsmanship");
        saved.setIsbn("978-0132350884");

        Book updated = bookRepository.save(saved);

        assertEquals("Clean Code: A Handbook of Agile Software Craftsmanship", updated.getTitle());
        assertEquals("978-0132350884", updated.getIsbn());
    }

    @Test
    void testDeleteBook() {
        Book book = new Book();
        book.setTitle("Clean Code");
        book.setAuthor("Robert C. Martin");
        book.setYear(2008);

        Book saved = bookRepository.save(book);
        long id = saved.getId();

        bookRepository.deleteById(id);

        assertFalse(bookRepository.existsById(id), "Book should be deleted");
    }

    @Test
    void testBookValidationConstraints() {
        // Test that validation fails for invalid data
        Book book = new Book();
        book.setTitle("a".repeat(256)); // Too long
        book.setAuthor("a".repeat(256)); // Too long
        book.setYear(2008);
        book.setIsbn("a".repeat(21)); // Too long

        // Validation should fail when trying to save
        jakarta.validation.ConstraintViolationException exception = assertThrows(
            jakarta.validation.ConstraintViolationException.class,
            () -> bookRepository.save(book),
            "Saving a book with invalid data should throw ConstraintViolationException"
        );
        // Verify the exception message contains validation error details
        assertNotNull(exception.getMessage());
    }
}
