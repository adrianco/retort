package com.example.books;

import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Application logic: validates input and delegates persistence to the repository.
 */
public final class BookService {

    private final BookRepository repository;

    public BookService(BookRepository repository) {
        this.repository = repository;
    }

    public Book create(Map<String, Object> body) {
        Book book = fromBody(body);
        return repository.create(book);
    }

    public List<Book> list(String authorFilter) {
        return repository.findAll(authorFilter);
    }

    public Optional<Book> get(long id) {
        return repository.findById(id);
    }

    public Optional<Book> update(long id, Map<String, Object> body) {
        Book book = fromBody(body);
        return repository.update(id, book);
    }

    public boolean delete(long id) {
        return repository.delete(id);
    }

    /**
     * Builds and validates a {@link Book} from a parsed request body.
     *
     * @throws ValidationException if title or author are missing/blank, or a
     *     field has the wrong type.
     */
    private Book fromBody(Map<String, Object> body) {
        String title = requiredString(body, "title");
        String author = requiredString(body, "author");
        Integer year = optionalInt(body, "year");
        String isbn = optionalString(body, "isbn");
        return new Book(0, title, author, year, isbn);
    }

    private static String requiredString(Map<String, Object> body, String field) {
        Object value = body.get(field);
        if (value == null) {
            throw new ValidationException("'" + field + "' is required");
        }
        if (!(value instanceof String)) {
            throw new ValidationException("'" + field + "' must be a string");
        }
        String s = ((String) value).trim();
        if (s.isEmpty()) {
            throw new ValidationException("'" + field + "' must not be blank");
        }
        return s;
    }

    private static String optionalString(Map<String, Object> body, String field) {
        Object value = body.get(field);
        if (value == null) {
            return null;
        }
        if (!(value instanceof String)) {
            throw new ValidationException("'" + field + "' must be a string");
        }
        return (String) value;
    }

    private static Integer optionalInt(Map<String, Object> body, String field) {
        Object value = body.get(field);
        if (value == null) {
            return null;
        }
        if (value instanceof Number) {
            double d = ((Number) value).doubleValue();
            if (d != Math.rint(d)) {
                throw new ValidationException("'" + field + "' must be an integer");
            }
            return (int) d;
        }
        throw new ValidationException("'" + field + "' must be a number");
    }
}
