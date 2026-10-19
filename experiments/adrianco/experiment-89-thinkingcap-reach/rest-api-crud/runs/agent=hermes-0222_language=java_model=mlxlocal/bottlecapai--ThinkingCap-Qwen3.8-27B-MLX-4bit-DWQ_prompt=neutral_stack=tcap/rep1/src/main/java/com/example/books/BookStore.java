package com.example.books;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.sql.Types;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.locks.ReentrantLock;

/**
 * SQLite-backed book repository. All access is serialized on a single
 * reentrant lock, which is safe for a single-process service.
 */
public class BookStore implements AutoCloseable {

    private final Connection conn;
    private final ReentrantLock lock = new ReentrantLock();

    public BookStore(String jdbcUrl) throws SQLException {
        this.conn = DriverManager.getConnection(jdbcUrl);
        try (Statement st = conn.createStatement()) {
            st.execute("PRAGMA journal_mode=WAL");
            st.execute(
                    "CREATE TABLE IF NOT EXISTS books (" +
                    " id INTEGER PRIMARY KEY AUTOINCREMENT," +
                    " title TEXT NOT NULL," +
                    " author TEXT NOT NULL," +
                    " year INTEGER," +
                    " isbn TEXT)");
        }
    }

    public Book create(String title, String author, Integer year, String isbn) {
        lock.lock();
        try (PreparedStatement ps = conn.prepareStatement(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                Statement.RETURN_GENERATED_KEYS)) {
            bind(ps, title, author, year, isbn);
            ps.executeUpdate();
            try (ResultSet keys = ps.getGeneratedKeys()) {
                keys.next();
                return new Book(keys.getLong(1), title, author, year, isbn);
            }
        } catch (SQLException e) {
            throw new BookException(500, "Database error: " + e.getMessage());
        } finally {
            lock.unlock();
        }
    }

    public List<Book> list(String author) {
        lock.lock();
        try (PreparedStatement ps = author == null
                ? conn.prepareStatement("SELECT id, title, author, year, isbn FROM books ORDER BY id")
                : conn.prepareStatement(
                        "SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id")) {
            if (author != null) {
                ps.setString(1, author);
            }
            try (ResultSet rs = ps.executeQuery()) {
                List<Book> books = new ArrayList<>();
                while (rs.next()) {
                    books.add(row(rs));
                }
                return books;
            }
        } catch (SQLException e) {
            throw new BookException(500, "Database error: " + e.getMessage());
        } finally {
            lock.unlock();
        }
    }

    public Optional<Book> get(long id) {
        lock.lock();
        try (PreparedStatement ps = conn.prepareStatement(
                "SELECT id, title, author, year, isbn FROM books WHERE id = ?")) {
            ps.setLong(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? Optional.of(row(rs)) : Optional.empty();
            }
        } catch (SQLException e) {
            throw new BookException(500, "Database error: " + e.getMessage());
        } finally {
            lock.unlock();
        }
    }

    /**
     * Updates a book. Title and author are always replaced; year and isbn are
     * only replaced when non-null (null keeps the existing value).
     * Throws a 404 {@link BookException} when the book does not exist.
     */
    public Book update(long id, String title, String author, Integer year, String isbn) {
        lock.lock();
        try {
            Book existing = get(id).orElseThrow(() -> new BookException(404, "Book not found"));
            Integer finalYear = year != null ? year : existing.year();
            String finalIsbn = isbn != null ? isbn : existing.isbn();
            try (PreparedStatement ps = conn.prepareStatement(
                    "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?")) {
                bind(ps, title, author, finalYear, finalIsbn);
                ps.setLong(5, id);
                if (ps.executeUpdate() == 0) {
                    throw new BookException(404, "Book not found");
                }
            }
            return new Book(id, title, author, finalYear, finalIsbn);
        } catch (SQLException e) {
            throw new BookException(500, "Database error: " + e.getMessage());
        } finally {
            lock.unlock();
        }
    }

    /**
     * Deletes a book by id. Returns true when a row was removed.
     */
    public boolean delete(long id) {
        lock.lock();
        try (PreparedStatement ps = conn.prepareStatement("DELETE FROM books WHERE id = ?")) {
            ps.setLong(1, id);
            return ps.executeUpdate() > 0;
        } catch (SQLException e) {
            throw new BookException(500, "Database error: " + e.getMessage());
        } finally {
            lock.unlock();
        }
    }

    private static void bind(PreparedStatement ps, String title, String author,
                             Integer year, String isbn) throws SQLException {
        ps.setString(1, title);
        ps.setString(2, author);
        if (year != null) {
            ps.setInt(3, year);
        } else {
            ps.setNull(3, Types.INTEGER);
        }
        if (isbn != null) {
            ps.setString(4, isbn);
        } else {
            ps.setNull(4, Types.VARCHAR);
        }
    }

    private static Book row(ResultSet rs) throws SQLException {
        int year = rs.getInt("year");
        boolean yearNull = rs.wasNull(); // must be read before accessing any other column
        return new Book(
                rs.getLong("id"),
                rs.getString("title"),
                rs.getString("author"),
                yearNull ? null : year,
                rs.getString("isbn"));
    }

    @Override
    public void close() throws SQLException {
        conn.close();
    }
}
