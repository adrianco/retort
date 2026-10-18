package com.example.books;

/**
 * Entry point. Configuration via environment variables:
 * <ul>
 *   <li>{@code PORT} – listen port (default 8080)</li>
 *   <li>{@code BOOKS_DB_PATH} – SQLite file path (default {@code books.db})</li>
 * </ul>
 */
public final class App {

    private App() {
    }

    public static void main(String[] args) throws Exception {
        int port = Integer.parseInt(System.getenv().getOrDefault("PORT", "8080"));
        String dbPath = System.getenv().getOrDefault("BOOKS_DB_PATH", "books.db");

        BookRepository repository = new BookRepository("jdbc:sqlite:" + dbPath);
        BookServer server = new BookServer(port, repository);
        server.start();
        System.out.println("Book service listening on http://localhost:" + server.port());

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            server.stop();
            try {
                repository.close();
            } catch (Exception ignored) {
                // best effort on shutdown
            }
        }));
    }
}
