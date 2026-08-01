package com.example.books;

import io.javalin.Javalin;
import io.javalin.http.HttpStatus;

import java.sql.SQLException;
import java.util.Map;

public final class BookApplication {
    private BookApplication() { }

    public static Javalin create(BookRepository repository) {
        Javalin app = Javalin.create();
        app.get("/health", ctx -> ctx.json(Map.of("status", "ok")));
        app.post("/books", ctx -> {
            BookRequest request = valid(ctx.bodyAsClass(BookRequest.class));
            ctx.status(HttpStatus.CREATED).json(repository.create(request));
        });
        app.get("/books", ctx -> ctx.json(repository.findAll(ctx.queryParam("author"))));
        app.get("/books/{id}", ctx -> repository.findById(id(ctx.pathParam("id")))
                .ifPresentOrElse(ctx::json, () -> notFound(ctx)));
        app.put("/books/{id}", ctx -> {
            BookRequest request = valid(ctx.bodyAsClass(BookRequest.class));
            repository.update(id(ctx.pathParam("id")), request)
                    .ifPresentOrElse(ctx::json, () -> notFound(ctx));
        });
        app.delete("/books/{id}", ctx -> {
            if (repository.delete(id(ctx.pathParam("id")))) ctx.status(HttpStatus.NO_CONTENT);
            else notFound(ctx);
        });
        app.exception(IllegalArgumentException.class, (error, ctx) ->
                ctx.status(HttpStatus.BAD_REQUEST).json(Map.of("error", error.getMessage())));
        app.exception(SQLException.class, (error, ctx) ->
                ctx.status(HttpStatus.INTERNAL_SERVER_ERROR).json(Map.of("error", "Database error")));
        return app;
    }

    static BookRequest valid(BookRequest request) {
        if (request == null || blank(request.title()) || blank(request.author()))
            throw new IllegalArgumentException("title and author are required");
        return new BookRequest(request.title().trim(), request.author().trim(), request.year(), request.isbn());
    }
    private static boolean blank(String value) { return value == null || value.isBlank(); }
    private static long id(String value) {
        try { return Long.parseLong(value); }
        catch (NumberFormatException e) { throw new IllegalArgumentException("id must be a number"); }
    }
    private static void notFound(io.javalin.http.Context ctx) { ctx.status(HttpStatus.NOT_FOUND).json(Map.of("error", "Book not found")); }

    public static void main(String[] args) throws Exception {
        String database = System.getenv().getOrDefault("BOOKS_DB_URL", "jdbc:sqlite:books.db");
        create(new BookRepository(database)).start(7000);
    }
}
