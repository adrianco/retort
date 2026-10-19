package com.example.books;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;

import java.io.IOException;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.List;

/**
 * Routes HTTP requests to the {@link BookStore} and renders JSON responses.
 *
 * <pre>
 * GET    /health          -&gt; {"status":"ok"}
 * GET    /books           -&gt; list all books (optional ?author= filter)
 * POST   /books           -&gt; create a book (201)
 * GET    /books/{id}      -&gt; fetch one book
 * PUT    /books/{id}      -&gt; update a book
 * DELETE /books/{id}      -&gt; delete a book (204)
 * </pre>
 */
public class BookApiHandler implements HttpHandler {

    private final BookStore store;

    public BookApiHandler(BookStore store) {
        this.store = store;
    }

    @Override
    public void handle(HttpExchange ex) throws IOException {
        try {
            String method = ex.getRequestMethod();
            String path = ex.getRequestURI().getPath();

            if (path.equals("/health")) {
                requireMethod(ex, method, "GET");
                send(ex, 200, Json.write(java.util.Map.of("status", "ok")));
                return;
            }

            if (path.equals("/books")) {
                switch (method) {
                    case "GET" -> {
                        String author = firstParam(ex, "author");
                        send(ex, 200, Json.write(store.list(author)));
                    }
                    case "POST" -> {
                        BookInput in = BookValidation.validate(Json.readBookInput(ex.getRequestBody().readAllBytes()));
                        Book book = store.create(in.title(), in.author(), in.year(), in.isbn());
                        ex.getResponseHeaders().set("Location", "/books/" + book.id());
                        send(ex, 201, Json.write(book));
                    }
                    default -> methodNotAllowed(ex, List.of("GET", "POST"));
                }
                return;
            }

            if (path.startsWith("/books/")) {
                String rest = path.substring("/books/".length());
                long id;
                try {
                    id = Long.parseLong(rest);
                } catch (NumberFormatException e) {
                    notFound(ex);
                    return;
                }
                switch (method) {
                    case "GET" -> send(ex, 200, Json.write(
                            store.get(id).orElseThrow(() -> new BookException(404, "Book not found"))));
                    case "PUT" -> {
                        BookInput in = BookValidation.validate(Json.readBookInput(ex.getRequestBody().readAllBytes()));
                        send(ex, 200, Json.write(
                                store.update(id, in.title(), in.author(), in.year(), in.isbn())));
                    }
                    case "DELETE" -> {
                        if (!store.delete(id)) {
                            throw new BookException(404, "Book not found");
                        }
                        send(ex, 204, null);
                    }
                    default -> methodNotAllowed(ex, List.of("GET", "PUT", "DELETE"));
                }
                return;
            }

            notFound(ex);
        } catch (BookException e) {
            send(ex, e.status(), Json.error(e.getMessage()));
        } catch (Exception e) {
            send(ex, 500, Json.error("Internal server error"));
        }
    }

    private static void requireMethod(HttpExchange ex, String method, String... allowed) {
        for (String a : allowed) {
            if (a.equalsIgnoreCase(method)) {
                return;
            }
        }
        ex.getResponseHeaders().set("Allow", String.join(", ", allowed));
        throw new BookException(405, "Method " + method + " not allowed");
    }

    private static void methodNotAllowed(HttpExchange ex, List<String> allowed) {
        ex.getResponseHeaders().set("Allow", String.join(", ", allowed));
        throw new BookException(405, "Method " + ex.getRequestMethod() + " not allowed");
    }

    private static void notFound(HttpExchange ex) throws IOException {
        send(ex, 404, Json.error("Not found"));
    }

    private static void send(HttpExchange ex, int status, byte[] body) throws IOException {
        byte[] bytes = body == null ? new byte[0] : body;
        if (bytes.length > 0) {
            ex.getResponseHeaders().set("Content-Type", "application/json");
        }
        ex.sendResponseHeaders(status, bytes.length == 0 ? -1 : bytes.length);
        if (bytes.length > 0) {
            ex.getResponseBody().write(bytes);
        }
        ex.getResponseBody().close();
    }

    private static String firstParam(HttpExchange ex, String name) {
        String query = ex.getRequestURI().getRawQuery();
        if (query == null) {
            return null;
        }
        for (String pair : query.split("&")) {
            int eq = pair.indexOf('=');
            if (eq < 0) {
                continue;
            }
            String key = URLDecoder.decode(pair.substring(0, eq), StandardCharsets.UTF_8);
            if (key.equals(name)) {
                return URLDecoder.decode(pair.substring(eq + 1), StandardCharsets.UTF_8);
            }
        }
        return null;
    }
}
