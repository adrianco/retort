package com.example.books;

import io.javalin.Javalin;
import io.javalin.http.HttpResponseException;
import io.javalin.http.HttpStatus;

import java.util.Map;

/**
 * Application entry point. Builds the Javalin server, wires the SQLite-backed
 * DAO and book routes, and starts listening.
 */
public class App {

    /** Default on-disk SQLite database file. */
    public static final String DEFAULT_DB = "jdbc:sqlite:books.db";

    public static void main(String[] args) {
        int port = Integer.parseInt(System.getenv().getOrDefault("PORT", "7070"));
        String jdbcUrl = System.getenv().getOrDefault("DB_URL", DEFAULT_DB);

        BookDao dao = new BookDao(jdbcUrl);
        Javalin app = create(dao);

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            app.stop();
            dao.close();
        }));

        app.start(port);
    }

    /**
     * Builds a fully-configured (but not yet started) Javalin app for the given
     * DAO. Exposed for tests so they can run against an in-memory database.
     */
    public static Javalin create(BookDao dao) {
        Javalin app = Javalin.create(config -> config.showJavalinBanner = false);

        new BookController(dao).register(app);

        // Validation / not-found errors (BadRequestResponse, NotFoundResponse, ...)
        // carry their own status and message; render them as a JSON error body.
        app.exception(HttpResponseException.class, (e, ctx) -> {
            ctx.status(e.getStatus()).json(Map.of("error", e.getMessage()));
        });

        // Any other uncaught error becomes a JSON 500 so clients always get JSON.
        app.exception(Exception.class, (e, ctx) -> {
            ctx.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .json(Map.of("error", "Internal server error"));
        });

        return app;
    }
}
