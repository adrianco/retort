package books;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.javalin.Javalin;
import io.javalin.http.Context;

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

    public static void main(String[] args) {
        int port = Integer.parseInt(System.getenv().getOrDefault("PORT", "8080"));
        String dbPath = System.getenv().getOrDefault("DB_PATH", "books.db");
        create(new BookRepository(dbPath)).start(port);
    }

    /** Builds the (unstarted) Javalin app. */
    public static Javalin create(BookRepository repo) {
        Javalin app = Javalin.create(cfg -> cfg.showJavalinBanner = false);

        app.get("/health", ctx -> ctx.json(Map.of("status", "ok")));

        app.post("/books", ctx -> ctx.status(201).json(repo.create(parseBook(ctx))));

        app.get("/books", ctx -> ctx.json(repo.list(ctx.queryParam("author"))));

        app.get("/books/{id}", ctx -> {
            long id = parseId(ctx);
            ctx.json(repo.find(id).orElseThrow(() -> notFound(id)));
        });

        app.put("/books/{id}", ctx -> {
            long id = parseId(ctx);
            Book input = parseBook(ctx);
            ctx.json(repo.update(id, input).orElseThrow(() -> notFound(id)));
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
            ctx.attribute("apiError", true);
            if (e.details != null) {
                ctx.json(Map.of("error", e.getMessage(), "details", e.details));
            } else {
                ctx.json(Map.of("error", e.getMessage()));
            }
        });
        app.exception(Exception.class, (e, ctx) -> {
            e.printStackTrace();
            ctx.status(500).json(Map.of("error", "Internal server error"));
        });
        app.error(404, ctx -> {
            // Unmatched routes get Javalin's plain-text body; replace it with JSON.
            if (ctx.attribute("apiError") == null) {
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
            throw new ApiException(400, "Invalid book id");
        }
    }

    /** Parses and validates the request body; throws a 400 ApiException listing every problem. */
    private static Book parseBook(Context ctx) {
        JsonNode node;
        try {
            node = MAPPER.readTree(ctx.body());
        } catch (JsonProcessingException e) {
            throw new ApiException(400, "Request body is not valid JSON");
        }
        if (node == null || !node.isObject()) {
            throw new ApiException(400, "Request body must be a JSON object");
        }

        List<String> errors = new ArrayList<>();
        String title = requiredText(node, "title", errors);
        String author = requiredText(node, "author", errors);

        Integer year = null;
        JsonNode y = node.get("year");
        if (y != null && !y.isNull()) {
            if (y.isIntegralNumber() && y.canConvertToInt()) {
                year = y.intValue();
            } else {
                errors.add("year must be an integer");
            }
        }

        String isbn = null;
        JsonNode i = node.get("isbn");
        if (i != null && !i.isNull()) {
            if (i.isTextual()) {
                isbn = i.asText().trim();
            } else {
                errors.add("isbn must be a string");
            }
        }

        if (!errors.isEmpty()) {
            throw new ApiException(400, "Validation failed", errors);
        }
        return new Book(null, title, author, year, isbn);
    }

    private static String requiredText(JsonNode node, String field, List<String> errors) {
        JsonNode v = node.get(field);
        if (v == null || v.isNull()) {
            errors.add(field + " is required");
        } else if (!v.isTextual()) {
            errors.add(field + " must be a string");
        } else if (v.asText().isBlank()) {
            errors.add(field + " must not be blank");
        } else {
            return v.asText().trim();
        }
        return null;
    }
}
