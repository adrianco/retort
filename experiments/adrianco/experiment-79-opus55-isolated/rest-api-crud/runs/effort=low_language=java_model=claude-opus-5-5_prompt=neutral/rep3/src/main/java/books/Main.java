package books;

public class Main {
    public static void main(String[] args) throws Exception {
        int port = Integer.parseInt(System.getenv().getOrDefault("PORT", "8080"));
        String dbPath = System.getenv().getOrDefault("BOOKS_DB", "books.db");

        BookRepository repo = new BookRepository("jdbc:sqlite:" + dbPath);
        BookServer server = new BookServer(repo, port);
        server.start();
        System.out.println("Book API listening on http://localhost:" + server.port() + " (db: " + dbPath + ")");
    }
}
