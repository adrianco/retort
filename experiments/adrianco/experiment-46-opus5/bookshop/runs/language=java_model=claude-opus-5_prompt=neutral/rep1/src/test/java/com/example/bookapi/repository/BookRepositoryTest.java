package com.example.bookapi.repository;

import com.example.bookapi.AbstractIntegrationTest;
import com.example.bookapi.model.Book;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DataAccessException;

import java.time.Instant;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class BookRepositoryTest extends AbstractIntegrationTest {

    private static final Instant NOW = Instant.parse("2024-01-01T00:00:00Z");

    @Autowired
    private BookRepository repository;

    @Test
    @DisplayName("Rows survive the trip through SQLite with nulls intact")
    void insertAndReadBack() {
        Book saved = repository.insert(new Book(null, "Dune", "Frank Herbert", null, null, NOW, NOW));

        assertThat(saved.id()).isNotNull();
        assertThat(repository.findById(saved.id())).hasValueSatisfying(found -> {
            assertThat(found.title()).isEqualTo("Dune");
            assertThat(found.year()).isNull();
            assertThat(found.isbn()).isNull();
            assertThat(found.createdAt()).isEqualTo(NOW);
        });

        // The row really is in the database, not just in a cache.
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM books", Integer.class)).isEqualTo(1);
    }

    @Test
    @DisplayName("findByAuthor ignores case and surrounding whitespace")
    void findByAuthorIsCaseInsensitive() {
        repository.insert(new Book(null, "Dune", "Frank Herbert", 1965, null, NOW, NOW));
        repository.insert(new Book(null, "Neuromancer", "William Gibson", 1984, null, NOW, NOW));

        List<Book> found = repository.findByAuthor("  FRANK herbert ");

        assertThat(found).singleElement().satisfies(b -> assertThat(b.title()).isEqualTo("Dune"));
        assertThat(repository.findByAuthor("Nobody")).isEmpty();
    }

    @Test
    @DisplayName("Update and delete report 0 rows for an unknown id")
    void updateAndDeleteReportMisses() {
        assertThat(repository.deleteById(999)).isZero();
        assertThat(repository.update(new Book(999L, "x", "y", null, null, NOW, NOW))).isZero();
        assertThat(repository.findById(999)).isEmpty();
    }

    @Test
    @DisplayName("The unique index rejects a duplicate ISBN even below the service layer")
    void duplicateIsbnViolatesTheIndex() {
        repository.insert(new Book(null, "Dune", "Frank Herbert", 1965, "0441172717", NOW, NOW));

        assertThatThrownBy(() ->
                repository.insert(new Book(null, "Dune again", "Frank Herbert", 1965, "0441172717", NOW, NOW)))
                .isInstanceOf(DataAccessException.class)
                .hasMessageContaining("UNIQUE constraint failed");
    }

    @Test
    @DisplayName("Books without an ISBN are exempt from the uniqueness rule")
    void multipleBooksMayHaveNoIsbn() {
        repository.insert(new Book(null, "Dune", "Frank Herbert", 1965, null, NOW, NOW));
        repository.insert(new Book(null, "Neuromancer", "William Gibson", 1984, null, NOW, NOW));

        assertThat(repository.findAll()).hasSize(2);
        assertThat(repository.existsByIsbn("0441172717", null)).isFalse();
    }
}
