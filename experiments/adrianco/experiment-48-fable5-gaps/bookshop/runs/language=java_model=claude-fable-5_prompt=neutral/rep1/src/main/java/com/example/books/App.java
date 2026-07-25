package com.example.books;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.javalin.Javalin;
import io.javalin.http.Context;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;

public final class App {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private App() {
    }

    public static Javalin create(BookDao dao) {
        Javalin app = Javalin.create(cfg -> cfg.showJavalinBanner = false);

        app.get("/health", ctx -> ctx.json(Map.of("status", "ok")));

        app.post("/books", ctx -> {
            Book book = readValidBook(ctx);
            if (book == null) {
                return;
            }
            ctx.status(201).json(dao.create(book));
        });

        app.get("/books", ctx -> {
            String author = ctx.queryParam("author");
            ctx.json(dao.findAll(author));
        });

        app.get("/books/{id}", ctx -> {
            Integer id = readId(ctx);
            if (id == null) {
                return;
            }
            Optional<Book> book = dao.findById(id);
            if (book.isPresent()) {
                ctx.json(book.get());
            } else {
                notFound(ctx, id);
            }
        });

        app.put("/books/{id}", ctx -> {
            Integer id = readId(ctx);
            if (id == null) {
                return;
            }
            Book book = readValidBook(ctx);
            if (book == null) {
                return;
            }
            if (dao.update(id, book)) {
                book.setId(id);
                ctx.json(book);
            } else {
                notFound(ctx, id);
            }
        });

        app.delete("/books/{id}", ctx -> {
            Integer id = readId(ctx);
            if (id == null) {
                return;
            }
            if (dao.delete(id)) {
                ctx.status(204);
            } else {
                notFound(ctx, id);
            }
        });

        app.exception(SQLException.class, (e, ctx) ->
                ctx.status(500).json(Map.of("error", "database error")));

        return app;
    }

    /**
     * Parses and validates the request body. Returns null after writing a 400
     * response if the body is not valid JSON or fails validation.
     */
    private static Book readValidBook(Context ctx) {
        Book book;
        try {
            book = MAPPER.readValue(ctx.body(), Book.class);
        } catch (JsonProcessingException e) {
            ctx.status(400).json(Map.of("error", "request body must be a valid JSON book object"));
            return null;
        }
        List<String> errors = new ArrayList<>();
        if (book.getTitle() == null || book.getTitle().isBlank()) {
            errors.add("title is required");
        }
        if (book.getAuthor() == null || book.getAuthor().isBlank()) {
            errors.add("author is required");
        }
        if (!errors.isEmpty()) {
            ctx.status(400).json(Map.of("error", "validation failed", "details", errors));
            return null;
        }
        book.setId(null);
        return book;
    }

    /** Parses the {id} path param. Returns null after writing a 400 response if non-numeric. */
    private static Integer readId(Context ctx) {
        try {
            return Integer.valueOf(ctx.pathParam("id"));
        } catch (NumberFormatException e) {
            ctx.status(400).json(Map.of("error", "id must be an integer"));
            return null;
        }
    }

    private static void notFound(Context ctx, int id) {
        ctx.status(404).json(Map.of("error", "book " + id + " not found"));
    }

    public static void main(String[] args) throws SQLException {
        String dbPath = System.getenv().getOrDefault("BOOKS_DB", "books.db");
        int port = Integer.parseInt(System.getenv().getOrDefault("PORT", "7070"));
        Connection conn = DriverManager.getConnection("jdbc:sqlite:" + dbPath);
        BookDao dao = new BookDao(conn);
        create(dao).start(port);
    }
}
