package books;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;

class BookRepositoryTest {
    @Test
    void dataPersistsAcrossReopen(@TempDir Path dir) throws Exception {
        String url = "jdbc:sqlite:" + dir.resolve("books.db");
        long id;
        try (BookRepository repo = new BookRepository(url)) {
            id = repo.create(new Book(null, "Dune", "Frank Herbert", 1965, null)).id();
        }
        try (BookRepository repo = new BookRepository(url)) {
            assertEquals(new Book(id, "Dune", "Frank Herbert", 1965, null), repo.find(id).orElseThrow());
        }
    }

    @Test
    void idsAreNotReusedAfterDelete() throws Exception {
        try (BookRepository repo = new BookRepository("jdbc:sqlite::memory:")) {
            long first = repo.create(new Book(null, "A", "B", null, null)).id();
            repo.delete(first);
            assertNotEquals(first, repo.create(new Book(null, "C", "D", null, null)).id());
        }
    }
}
