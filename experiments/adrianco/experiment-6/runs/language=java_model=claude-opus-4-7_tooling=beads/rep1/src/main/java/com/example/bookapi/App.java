package com.example.bookapi;

import io.javalin.Javalin;
import io.javalin.http.HttpStatus;

import java.util.Map;

public class App {

    public static void main(String[] args) {
        String dbUrl = System.getenv().getOrDefault("DB_URL", "jdbc:sqlite:books.db");
        int port = Integer.parseInt(System.getenv().getOrDefault("PORT", "7070"));
        Javalin app = create(new BookRepository(dbUrl));
        app.start(port);
    }

    public static Javalin create(BookRepository repo) {
        Javalin app = Javalin.create();

        app.get("/health", ctx -> ctx.json(Map.of("status", "ok")));

        app.post("/books", ctx -> {
            Book book = ctx.bodyAsClass(Book.class);
            String error = validate(book);
            if (error != null) {
                ctx.status(HttpStatus.BAD_REQUEST).json(Map.of("error", error));
                return;
            }
            Book created = repo.create(book);
            ctx.status(HttpStatus.CREATED).json(created);
        });

        app.get("/books", ctx -> {
            String author = ctx.queryParam("author");
            ctx.json(repo.findAll(author));
        });

        app.get("/books/{id}", ctx -> {
            Long id = parseId(ctx.pathParam("id"));
            if (id == null) {
                ctx.status(HttpStatus.BAD_REQUEST).json(Map.of("error", "Invalid id"));
                return;
            }
            repo.findById(id).ifPresentOrElse(
                    ctx::json,
                    () -> ctx.status(HttpStatus.NOT_FOUND).json(Map.of("error", "Book not found"))
            );
        });

        app.put("/books/{id}", ctx -> {
            Long id = parseId(ctx.pathParam("id"));
            if (id == null) {
                ctx.status(HttpStatus.BAD_REQUEST).json(Map.of("error", "Invalid id"));
                return;
            }
            Book book = ctx.bodyAsClass(Book.class);
            String error = validate(book);
            if (error != null) {
                ctx.status(HttpStatus.BAD_REQUEST).json(Map.of("error", error));
                return;
            }
            repo.update(id, book).ifPresentOrElse(
                    ctx::json,
                    () -> ctx.status(HttpStatus.NOT_FOUND).json(Map.of("error", "Book not found"))
            );
        });

        app.delete("/books/{id}", ctx -> {
            Long id = parseId(ctx.pathParam("id"));
            if (id == null) {
                ctx.status(HttpStatus.BAD_REQUEST).json(Map.of("error", "Invalid id"));
                return;
            }
            if (repo.delete(id)) {
                ctx.status(HttpStatus.NO_CONTENT);
            } else {
                ctx.status(HttpStatus.NOT_FOUND).json(Map.of("error", "Book not found"));
            }
        });

        app.exception(Exception.class, (e, ctx) -> {
            ctx.status(HttpStatus.INTERNAL_SERVER_ERROR).json(Map.of("error", e.getMessage() == null ? "Internal error" : e.getMessage()));
        });

        return app;
    }

    private static String validate(Book book) {
        if (book == null) return "Body is required";
        if (book.getTitle() == null || book.getTitle().isBlank()) return "title is required";
        if (book.getAuthor() == null || book.getAuthor().isBlank()) return "author is required";
        return null;
    }

    private static Long parseId(String raw) {
        try {
            return Long.parseLong(raw);
        } catch (NumberFormatException e) {
            return null;
        }
    }
}
