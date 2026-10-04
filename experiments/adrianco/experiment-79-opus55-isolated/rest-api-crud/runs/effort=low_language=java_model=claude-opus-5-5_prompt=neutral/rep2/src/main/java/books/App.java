package books;

public class App {
    public static void main(String[] args) throws Exception {
        int port = Integer.parseInt(env("PORT", "8080"));
        String dbPath = env("DB_PATH", "books.db");

        BookRepository repo = new BookRepository("jdbc:sqlite:" + dbPath);
        BookServer server = new BookServer(repo, port);
        server.start();
        System.out.println("Books API listening on http://localhost:" + server.port() + " (db: " + dbPath + ")");
    }

    private static String env(String name, String fallback) {
        String value = System.getenv(name);
        return value == null || value.isBlank() ? fallback : value;
    }
}
