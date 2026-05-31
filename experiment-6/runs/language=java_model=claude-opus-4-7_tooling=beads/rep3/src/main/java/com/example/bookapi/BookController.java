package com.example.bookapi;

import io.javalin.http.Context;
import io.javalin.http.HttpStatus;

import java.util.LinkedHashMap;
import java.util.Map;

public class BookController {
    private final BookRepository repo;

    public BookController(BookRepository repo) {
        this.repo = repo;
    }

    public void create(Context ctx) {
        Book body = parseBody(ctx);
        String error = validate(body);
        if (error != null) {
            ctx.status(HttpStatus.BAD_REQUEST).json(Map.of("error", error));
            return;
        }
        Book created = repo.create(body);
        ctx.status(HttpStatus.CREATED).json(created);
    }

    public void list(Context ctx) {
        String author = ctx.queryParam("author");
        ctx.status(HttpStatus.OK).json(repo.findAll(author));
    }

    public void get(Context ctx) {
        Long id = parseId(ctx);
        if (id == null) return;
        repo.findById(id).ifPresentOrElse(
                book -> ctx.status(HttpStatus.OK).json(book),
                () -> ctx.status(HttpStatus.NOT_FOUND).json(Map.of("error", "Book not found")));
    }

    public void update(Context ctx) {
        Long id = parseId(ctx);
        if (id == null) return;
        Book body = parseBody(ctx);
        String error = validate(body);
        if (error != null) {
            ctx.status(HttpStatus.BAD_REQUEST).json(Map.of("error", error));
            return;
        }
        repo.update(id, body).ifPresentOrElse(
                book -> ctx.status(HttpStatus.OK).json(book),
                () -> ctx.status(HttpStatus.NOT_FOUND).json(Map.of("error", "Book not found")));
    }

    public void delete(Context ctx) {
        Long id = parseId(ctx);
        if (id == null) return;
        if (repo.delete(id)) {
            ctx.status(HttpStatus.NO_CONTENT);
        } else {
            ctx.status(HttpStatus.NOT_FOUND).json(Map.of("error", "Book not found"));
        }
    }

    public void health(Context ctx) {
        Map<String, String> body = new LinkedHashMap<>();
        body.put("status", "UP");
        ctx.status(HttpStatus.OK).json(body);
    }

    private Book parseBody(Context ctx) {
        try {
            return ctx.bodyAsClass(Book.class);
        } catch (Exception e) {
            ctx.status(HttpStatus.BAD_REQUEST).json(Map.of("error", "Invalid JSON body"));
            throw new BadRequestSignal();
        }
    }

    private Long parseId(Context ctx) {
        try {
            return Long.parseLong(ctx.pathParam("id"));
        } catch (NumberFormatException e) {
            ctx.status(HttpStatus.BAD_REQUEST).json(Map.of("error", "Invalid id"));
            return null;
        }
    }

    private String validate(Book b) {
        if (b == null) return "Request body is required";
        if (b.getTitle() == null || b.getTitle().isBlank()) return "title is required";
        if (b.getAuthor() == null || b.getAuthor().isBlank()) return "author is required";
        return null;
    }

    static class BadRequestSignal extends RuntimeException {}
}
