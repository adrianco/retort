package com.example.books;

import io.javalin.Javalin;
import io.javalin.http.BadRequestResponse;
import io.javalin.http.Context;
import io.javalin.http.NotFoundResponse;

import java.util.Map;

/**
 * Wires the REST endpoints for the book collection onto a Javalin instance.
 */
public class BookController {

    private final BookDao dao;

    public BookController(BookDao dao) {
        this.dao = dao;
    }

    /** Registers all routes on the given Javalin app. */
    public void register(Javalin app) {
        app.get("/health", this::health);
        app.post("/books", this::create);
        app.get("/books", this::list);
        app.get("/books/{id}", this::getOne);
        app.put("/books/{id}", this::update);
        app.delete("/books/{id}", this::delete);
    }

    private void health(Context ctx) {
        ctx.json(Map.of("status", "ok"));
    }

    private void create(Context ctx) {
        Book book = parseBody(ctx);
        validate(book);
        Book created = dao.create(book);
        ctx.status(201).json(created);
    }

    private void list(Context ctx) {
        String author = ctx.queryParam("author");
        ctx.json(dao.findAll(author));
    }

    private void getOne(Context ctx) {
        long id = parseId(ctx);
        Book book = dao.findById(id)
                .orElseThrow(() -> new NotFoundResponse("Book " + id + " not found"));
        ctx.json(book);
    }

    private void update(Context ctx) {
        long id = parseId(ctx);
        Book book = parseBody(ctx);
        validate(book);
        Book updated = dao.update(id, book)
                .orElseThrow(() -> new NotFoundResponse("Book " + id + " not found"));
        ctx.json(updated);
    }

    private void delete(Context ctx) {
        long id = parseId(ctx);
        if (!dao.delete(id)) {
            throw new NotFoundResponse("Book " + id + " not found");
        }
        ctx.status(204);
    }

    private Book parseBody(Context ctx) {
        try {
            Book book = ctx.bodyAsClass(Book.class);
            if (book == null) {
                throw new BadRequestResponse("Request body is required");
            }
            return book;
        } catch (BadRequestResponse e) {
            throw e;
        } catch (Exception e) {
            throw new BadRequestResponse("Malformed JSON request body");
        }
    }

    private long parseId(Context ctx) {
        try {
            return Long.parseLong(ctx.pathParam("id"));
        } catch (NumberFormatException e) {
            throw new BadRequestResponse("Invalid book id: " + ctx.pathParam("id"));
        }
    }

    private void validate(Book book) {
        if (isBlank(book.getTitle())) {
            throw new BadRequestResponse("Field 'title' is required");
        }
        if (isBlank(book.getAuthor())) {
            throw new BadRequestResponse("Field 'author' is required");
        }
    }

    private static boolean isBlank(String s) {
        return s == null || s.isBlank();
    }
}
