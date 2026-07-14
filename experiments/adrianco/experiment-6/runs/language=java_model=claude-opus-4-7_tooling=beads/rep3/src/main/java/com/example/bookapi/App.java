package com.example.bookapi;

import io.javalin.Javalin;

public class App {

    public static Javalin createApp(BookRepository repo) {
        BookController controller = new BookController(repo);
        Javalin app = Javalin.create(config -> {
            config.showJavalinBanner = false;
        });

        app.exception(BookController.BadRequestSignal.class, (e, ctx) -> {
            // already wrote a response in parseBody
        });

        app.get("/health", controller::health);
        app.post("/books", controller::create);
        app.get("/books", controller::list);
        app.get("/books/{id}", controller::get);
        app.put("/books/{id}", controller::update);
        app.delete("/books/{id}", controller::delete);

        return app;
    }

    public static void main(String[] args) {
        String dbPath = System.getenv().getOrDefault("BOOKS_DB_PATH", "books.db");
        String jdbcUrl = "jdbc:sqlite:" + dbPath;
        int port = Integer.parseInt(System.getenv().getOrDefault("PORT", "8080"));

        BookRepository repo = new BookRepository(jdbcUrl);
        Javalin app = createApp(repo);
        app.start(port);
    }
}
