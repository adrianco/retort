package com.example.books;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.javalin.Javalin;
import io.javalin.http.Context;
import io.javalin.http.HttpStatus;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;

public class App {

    private final BookDao dao;
    private final Javalin app;

    public App(String jdbcUrl) {
        this.dao = new BookDao(jdbcUrl);
        this.app = Javalin.create();
        registerRoutes();
    }

    public Javalin javalin() {
        return app;
    }

    public App start(int port) {
        app.start(port);
        return this;
    }

    public void stop() {
        app.stop();
    }

    public int port() {
        return app.port();
    }

    private void registerRoutes() {
        app.get("/health", this::health);
        app.post("/books", this::createBook);
        app.get("/books", this::listBooks);
        app.get("/books/{id}", this::getBook);
        app.put("/books/{id}", this::updateBook);
        app.delete("/books/{id}", this::deleteBook);

        app.exception(NumberFormatException.class, (e, ctx) ->
                error(ctx, HttpStatus.BAD_REQUEST, "Invalid id"));
    }

    private void health(Context ctx) {
        ctx.json(Map.of("status", "ok"));
    }

    private void createBook(Context ctx) {
        Book input;
        try {
            input = ctx.bodyAsClass(Book.class);
        } catch (Exception e) {
            error(ctx, HttpStatus.BAD_REQUEST, "Invalid JSON body");
            return;
        }
        String validation = validate(input);
        if (validation != null) {
            error(ctx, HttpStatus.BAD_REQUEST, validation);
            return;
        }
        input.setId(null);
        Book created = dao.create(input);
        ctx.status(HttpStatus.CREATED).json(created);
    }

    private void listBooks(Context ctx) {
        String author = ctx.queryParam("author");
        ctx.json(dao.findAll(author));
    }

    private void getBook(Context ctx) {
        long id = Long.parseLong(ctx.pathParam("id"));
        Optional<Book> book = dao.findById(id);
        if (book.isEmpty()) {
            error(ctx, HttpStatus.NOT_FOUND, "Book not found");
            return;
        }
        ctx.json(book.get());
    }

    private void updateBook(Context ctx) {
        long id = Long.parseLong(ctx.pathParam("id"));
        Book input;
        try {
            input = ctx.bodyAsClass(Book.class);
        } catch (Exception e) {
            error(ctx, HttpStatus.BAD_REQUEST, "Invalid JSON body");
            return;
        }
        String validation = validate(input);
        if (validation != null) {
            error(ctx, HttpStatus.BAD_REQUEST, validation);
            return;
        }
        Optional<Book> updated = dao.update(id, input);
        if (updated.isEmpty()) {
            error(ctx, HttpStatus.NOT_FOUND, "Book not found");
            return;
        }
        ctx.json(updated.get());
    }

    private void deleteBook(Context ctx) {
        long id = Long.parseLong(ctx.pathParam("id"));
        if (!dao.delete(id)) {
            error(ctx, HttpStatus.NOT_FOUND, "Book not found");
            return;
        }
        ctx.status(HttpStatus.NO_CONTENT);
    }

    private static String validate(Book b) {
        if (b == null) return "Body is required";
        if (b.getTitle() == null || b.getTitle().isBlank()) return "title is required";
        if (b.getAuthor() == null || b.getAuthor().isBlank()) return "author is required";
        return null;
    }

    private static void error(Context ctx, HttpStatus status, String message) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("error", message);
        ctx.status(status).json(body);
    }

    public static void main(String[] args) {
        String jdbcUrl = System.getenv().getOrDefault("BOOKS_DB_URL", "jdbc:sqlite:books.db");
        int port = Integer.parseInt(System.getenv().getOrDefault("PORT", "7070"));
        new App(jdbcUrl).start(port);
    }
}
