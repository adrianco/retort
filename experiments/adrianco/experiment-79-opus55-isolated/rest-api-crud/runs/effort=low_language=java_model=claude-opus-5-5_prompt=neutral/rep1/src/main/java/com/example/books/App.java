package com.example.books;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.javalin.Javalin;
import io.javalin.http.Context;

import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class App {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    /** Thrown for client errors; mapped to a JSON error response. */
    static class ApiException extends RuntimeException {
        final int status;
        final List<String> details;

        ApiException(int status, String message, List<String> details) {
            super(message);
            this.status = status;
            this.details = details;
        }

        ApiException(int status, String message) {
            this(status, message, null);
        }
    }

    public static void main(String[] args) throws SQLException {
        int port = Integer.parseInt(System.getenv().getOrDefault("PORT", "8080"));
        String dbPath = System.getenv().getOrDefault("DB_PATH", "books.db");
        BookRepository repo = new BookRepository("jdbc:sqlite:" + dbPath);
        create(repo).start(port);
    }

    /** Builds the (unstarted) server on top of the given repository. */
    public static Javalin create(BookRepository repo) {
        Javalin app = Javalin.create(config -> config.showJavalinBanner = false);

        app.get("/health", ctx -> ctx.json(Map.of("status", "ok")));

        app.post("/books", ctx -> ctx.status(201).json(repo.create(parseBook(ctx))));

        app.get("/books", ctx -> ctx.json(repo.list(ctx.queryParam("author"))));

        app.get("/books/{id}", ctx -> {
            long id = parseId(ctx);
            ctx.json(repo.find(id).orElseThrow(() -> notFound(id)));
        });

        app.put("/books/{id}", ctx -> {
            long id = parseId(ctx);
            ctx.json(repo.update(id, parseBook(ctx)).orElseThrow(() -> notFound(id)));
        });

        app.delete("/books/{id}", ctx -> {
            long id = parseId(ctx);
            if (!repo.delete(id)) {
                throw notFound(id);
            }
            ctx.status(204);
        });

        app.exception(ApiException.class, (e, ctx) -> {
            ctx.status(e.status);
            if (e.details == null) {
                ctx.json(Map.of("error", e.getMessage()));
            } else {
                ctx.json(Map.of("error", e.getMessage(), "details", e.details));
            }
        });
        app.exception(Exception.class, (e, ctx) -> {
            e.printStackTrace();
            ctx.status(500).json(Map.of("error", "Internal server error"));
        });
        app.error(404, ctx -> {
            // Unmatched routes get Javalin's plain-text body; book 404s are already JSON.
            String contentType = ctx.res().getContentType();
            if (contentType == null || !contentType.startsWith("application/json")) {
                ctx.json(Map.of("error", "Not found"));
            }
        });

        return app;
    }

    private static ApiException notFound(long id) {
        return new ApiException(404, "Book " + id + " not found");
    }

    private static long parseId(Context ctx) {
        try {
            return Long.parseLong(ctx.pathParam("id"));
        } catch (NumberFormatException e) {
            throw new ApiException(400, "Book id must be an integer");
        }
    }

    /** Parses and validates a book from the request body. */
    private static Book parseBook(Context ctx) {
        JsonNode body;
        try {
            body = MAPPER.readTree(ctx.body());
        } catch (JsonProcessingException e) {
            throw new ApiException(400, "Request body is not valid JSON");
        }
        if (body == null || !body.isObject()) {
            throw new ApiException(400, "Request body must be a JSON object");
        }

        List<String> errors = new ArrayList<>();
        String title = requiredText(body, "title", errors);
        String author = requiredText(body, "author", errors);

        Integer year = null;
        JsonNode yearNode = body.get("year");
        if (yearNode != null && !yearNode.isNull()) {
            if (yearNode.isIntegralNumber() && yearNode.canConvertToInt()) {
                year = yearNode.intValue();
            } else {
                errors.add("year must be an integer");
            }
        }

        String isbn = null;
        JsonNode isbnNode = body.get("isbn");
        if (isbnNode != null && !isbnNode.isNull()) {
            if (isbnNode.isTextual()) {
                isbn = isbnNode.textValue().trim();
            } else {
                errors.add("isbn must be a string");
            }
        }

        if (!errors.isEmpty()) {
            throw new ApiException(400, "Validation failed", errors);
        }
        return new Book(null, title, author, year, isbn);
    }

    private static String requiredText(JsonNode body, String field, List<String> errors) {
        JsonNode node = body.get(field);
        if (node == null || node.isNull()) {
            errors.add(field + " is required");
        } else if (!node.isTextual()) {
            errors.add(field + " must be a string");
        } else if (node.textValue().isBlank()) {
            errors.add(field + " is required");
        } else {
            return node.textValue().trim();
        }
        return null;
    }
}
