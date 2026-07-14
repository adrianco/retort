package com.example.books;

import java.io.IOException;

/**
 * Entry point: starts the Book collection REST API server.
 *
 * <p>Configuration via environment variables:
 * <ul>
 *   <li>{@code PORT} — port to listen on (default 8080)</li>
 *   <li>{@code DB_URL} — JDBC URL (default {@code jdbc:sqlite:books.db})</li>
 * </ul>
 */
public final class Main {

    private Main() {
    }

    public static void main(String[] args) throws IOException {
        int port = parsePort(System.getenv("PORT"), 8080);
        String dbUrl = envOrDefault("DB_URL", "jdbc:sqlite:books.db");

        BookRepository repository = new BookRepository(dbUrl);
        BookService service = new BookService(repository);
        ApiServer server = new ApiServer(port, service);

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            server.stop();
            repository.close();
        }));

        server.start();
        System.out.println("Book API listening on http://localhost:" + server.port());
        System.out.println("Database: " + dbUrl);
    }

    private static int parsePort(String value, int fallback) {
        if (value == null || value.isBlank()) {
            return fallback;
        }
        try {
            return Integer.parseInt(value.trim());
        } catch (NumberFormatException e) {
            return fallback;
        }
    }

    private static String envOrDefault(String name, String fallback) {
        String value = System.getenv(name);
        return (value == null || value.isBlank()) ? fallback : value;
    }
}
