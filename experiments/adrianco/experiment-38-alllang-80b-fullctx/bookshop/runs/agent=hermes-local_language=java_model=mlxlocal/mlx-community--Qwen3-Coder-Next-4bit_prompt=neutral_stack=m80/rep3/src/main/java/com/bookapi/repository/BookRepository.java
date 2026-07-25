package com.bookapi.repository;

import com.bookapi.model.Book;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.sql.*;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

public class BookRepository {
    private static final Logger logger = LoggerFactory.getLogger(BookRepository.class);
    private static final String DEFAULT_DB_URL = "jdbc:sqlite:books.db";
    private static final String CREATE_TABLE_SQL = 
        "CREATE TABLE IF NOT EXISTS books (" +
        "id INTEGER PRIMARY KEY AUTOINCREMENT, " +
        "title TEXT NOT NULL, " +
        "author TEXT NOT NULL, " +
        "year INTEGER NOT NULL, " +
        "isbn TEXT)";
    
    private final String dbUrl;

    public BookRepository() {
        this(DEFAULT_DB_URL);
    }

    public BookRepository(String dbUrl) {
        this.dbUrl = dbUrl;
        initializeDatabase();
    }

    private void initializeDatabase() {
        try (Connection conn = DriverManager.getConnection(dbUrl)) {
            conn.createStatement().execute(CREATE_TABLE_SQL);
            logger.info("Database initialized successfully");
        } catch (SQLException e) {
            logger.error("Error initializing database", e);
            throw new RuntimeException("Failed to initialize database", e);
        }
    }

    public Optional<Book> findById(int id) {
        String sql = "SELECT id, title, author, year, isbn FROM books WHERE id = ?";
        try (Connection conn = DriverManager.getConnection(dbUrl);
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            stmt.setInt(1, id);
            ResultSet rs = stmt.executeQuery();
            if (rs.next()) {
                return Optional.of(mapRow(rs));
            }
        } catch (SQLException e) {
            logger.error("Error finding book by id", e);
        }
        return Optional.empty();
    }

    public List<Book> findAll(String authorFilter) {
        List<Book> books = new ArrayList<>();
        String sql;
        
        if (authorFilter != null && !authorFilter.isEmpty()) {
            sql = "SELECT id, title, author, year, isbn FROM books WHERE author LIKE ?";
        } else {
            sql = "SELECT id, title, author, year, isbn FROM books";
        }
        
        try (Connection conn = DriverManager.getConnection(dbUrl);
             PreparedStatement stmt = authorFilter != null && !authorFilter.isEmpty() 
                 ? conn.prepareStatement(sql) 
                 : conn.prepareStatement(sql)) {
            
            if (authorFilter != null && !authorFilter.isEmpty()) {
                stmt.setString(1, "%" + authorFilter + "%");
            }
            
            ResultSet rs = stmt.executeQuery();
            while (rs.next()) {
                books.add(mapRow(rs));
            }
        } catch (SQLException e) {
            logger.error("Error finding all books", e);
        }
        return books;
    }

    public Book save(Book book) {
        String sql;
        if (book.getId() != null) {
            sql = "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?";
        } else {
            sql = "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)";
        }
        
        try (Connection conn = DriverManager.getConnection(dbUrl);
             PreparedStatement stmt = conn.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)) {
            
            int paramIndex = 1;
            stmt.setString(paramIndex++, book.getTitle());
            stmt.setString(paramIndex++, book.getAuthor());
            stmt.setInt(paramIndex++, book.getYear());
            if (book.getIsbn() != null) {
                stmt.setString(paramIndex++, book.getIsbn());
            } else {
                stmt.setNull(paramIndex++, Types.VARCHAR);
            }
            
            if (book.getId() != null) {
                stmt.setInt(paramIndex, book.getId());
            }
            
            int rowsAffected = stmt.executeUpdate();
            if (rowsAffected > 0) {
                if (book.getId() == null) {
                    ResultSet rs = stmt.getGeneratedKeys();
                    if (rs.next()) {
                        book.setId(rs.getInt(1));
                    }
                }
                return book;
            }
        } catch (SQLException e) {
            logger.error("Error saving book", e);
        }
        return null;
    }

    public boolean delete(int id) {
        String sql = "DELETE FROM books WHERE id = ?";
        try (Connection conn = DriverManager.getConnection(dbUrl);
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            stmt.setInt(1, id);
            int rowsAffected = stmt.executeUpdate();
            return rowsAffected > 0;
        } catch (SQLException e) {
            logger.error("Error deleting book", e);
            return false;
        }
    }

    private Book mapRow(ResultSet rs) throws SQLException {
        Book book = new Book();
        book.setId(rs.getInt("id"));
        book.setTitle(rs.getString("title"));
        book.setAuthor(rs.getString("author"));
        book.setYear(rs.getInt("year"));
        book.setIsbn(rs.getString("isbn"));
        return book;
    }
}
