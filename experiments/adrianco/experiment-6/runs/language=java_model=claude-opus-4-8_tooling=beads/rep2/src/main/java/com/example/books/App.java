package com.example.books;

import java.io.IOException;

/**
 * Application entry point. Starts the {@link BookServer} backed by a
 * file-based SQLite database.
 */
public class App {

    public static void main(String[] args) throws IOException {
        int port = Integer.parseInt(envOrDefault("PORT", "8080"));
        String dbPath = envOrDefault("DB_PATH", "books.db");
        String jdbcUrl = "jdbc:sqlite:" + dbPath;

        BookRepository repository = new BookRepository(jdbcUrl);
        BookServer server = new BookServer(port, repository);
        server.start();

        System.out.println("Book collection API listening on http://localhost:" + server.getPort());
        System.out.println("Database: " + dbPath);

        Runtime.getRuntime().addShutdownHook(new Thread(server::stop));
    }

    private static String envOrDefault(String key, String fallback) {
        String value = System.getenv(key);
        return (value == null || value.isBlank()) ? fallback : value;
    }
}
