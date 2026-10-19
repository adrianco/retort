package com.example.books;

import com.sun.net.httpserver.HttpServer;

import java.net.InetSocketAddress;
import java.sql.SQLException;
import java.util.concurrent.Executors;

/**
 * Entry point. Starts the book REST API on a configurable port.
 *
 * <ul>
 *   <li>{@code PORT} env var (default 8080) or first program argument</li>
 *   <li>{@code BOOK_DB} env var (default books.db) or second program argument</li>
 * </ul>
 */
public final class BookApp {

    private BookApp() {
    }

    public static void main(String[] args) throws Exception {
        String envPort = System.getenv("PORT");
        String envDb = System.getenv("BOOK_DB");
        int port = args.length > 0 ? Integer.parseInt(args[0]) : Integer.parseInt(envPort != null ? envPort : "8080");
        String dbPath = args.length > 1 ? args[1] : envDb != null ? envDb : "books.db";

        BookStore store = new BookStore("jdbc:sqlite:" + dbPath);
        HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);
        server.createContext("/", new BookApiHandler(store));
        server.setExecutor(Executors.newFixedThreadPool(8));
        server.start();

        System.out.println("Book API listening on http://localhost:" + server.getAddress().getPort()
                + " (db: " + dbPath + ")");
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            server.stop(0);
            try {
                store.close();
            } catch (SQLException ignored) {
                // best effort on shutdown
            }
        }));
    }
}
