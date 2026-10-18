package com.example.books;

import java.io.IOException;

/**
 * Starts the book API.
 *
 * <p>Configuration (environment variables, both optional):
 * <ul>
 *   <li>{@code PORT} — HTTP port, default 8080</li>
 *   <li>{@code DB_PATH} — SQLite file path, default {@code books.db}</li>
 * </ul>
 */
public final class Main {

    private Main() {
    }

    public static void main(String[] args) throws IOException {
        int port = Integer.parseInt(System.getenv().getOrDefault("PORT", "8080"));
        String dbPath = System.getenv().getOrDefault("DB_PATH", "books.db");

        BookRepository repository = new BookRepository("jdbc:sqlite:" + dbPath);
        BookServer server = new BookServer(repository);
        int bound = server.start(port);

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            server.stop();
            repository.close();
        }));
        System.out.println("Book API listening on http://localhost:" + bound + " (db: " + dbPath + ")");
    }
}
