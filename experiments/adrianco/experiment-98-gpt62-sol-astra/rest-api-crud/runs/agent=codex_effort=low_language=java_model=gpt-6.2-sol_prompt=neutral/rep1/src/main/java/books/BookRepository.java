package books;

import java.util.List;
import java.util.Optional;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

@Repository
class BookRepository {
    private static final RowMapper<Book> BOOK = (row, index) -> {
        int year = row.getInt("year");
        Integer publicationYear = row.wasNull() ? null : year;
        return new Book(row.getLong("id"), row.getString("title"), row.getString("author"),
                publicationYear, row.getString("isbn"));
    };

    private final JdbcClient jdbc;

    BookRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    Book create(Book.Input book) {
        return fields("""
                INSERT INTO books (title, author, year, isbn)
                VALUES (:title, :author, :year, :isbn)
                RETURNING id, title, author, year, isbn
                """, book).query(BOOK).single();
    }

    List<Book> list(String author) {
        if (author == null) {
            return jdbc.sql("SELECT * FROM books ORDER BY id").query(BOOK).list();
        }
        return jdbc.sql("SELECT * FROM books WHERE author = :author ORDER BY id")
                .param("author", author).query(BOOK).list();
    }

    Optional<Book> find(long id) {
        return jdbc.sql("SELECT * FROM books WHERE id = :id")
                .param("id", id).query(BOOK).optional();
    }

    Optional<Book> update(long id, Book.Input book) {
        return fields("""
                UPDATE books SET title = :title, author = :author, year = :year, isbn = :isbn
                WHERE id = :id
                RETURNING id, title, author, year, isbn
                """, book).param("id", id).query(BOOK).optional();
    }

    boolean delete(long id) {
        return jdbc.sql("DELETE FROM books WHERE id = :id").param("id", id).update() > 0;
    }

    private JdbcClient.StatementSpec fields(String sql, Book.Input book) {
        return jdbc.sql(sql).param("title", book.title()).param("author", book.author())
                .param("year", book.year()).param("isbn", book.isbn());
    }
}
