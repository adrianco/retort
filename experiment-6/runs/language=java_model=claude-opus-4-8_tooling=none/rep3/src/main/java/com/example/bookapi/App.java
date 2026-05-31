package com.example.bookapi;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.util.Map;
import java.util.concurrent.Executors;

/**
 * Bootstraps the book collection REST API on top of the JDK HttpServer.
 */
public class App {

    private final HttpServer server;
    private final BookRepository repository;

    public App(int port, String jdbcUrl) throws IOException {
        this.repository = new BookRepository(jdbcUrl);
        this.server = HttpServer.create(new InetSocketAddress(port), 0);
        this.server.createContext("/books", new BookHandler(repository));
        this.server.createContext("/health", App::health);
        this.server.setExecutor(Executors.newFixedThreadPool(8));
    }

    public void start() {
        server.start();
    }

    public void stop() {
        server.stop(0);
        repository.close();
    }

    /** Actual bound port (useful when constructed with port 0). */
    public int port() {
        return server.getAddress().getPort();
    }

    private static void health(HttpExchange exchange) throws IOException {
        try {
            byte[] payload = new ObjectMapper()
                    .writeValueAsBytes(Map.of("status", "ok"));
            exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
            exchange.sendResponseHeaders(200, payload.length);
            try (OutputStream os = exchange.getResponseBody()) {
                os.write(payload);
            }
        } finally {
            exchange.close();
        }
    }

    public static void main(String[] args) throws IOException {
        int port = Integer.parseInt(System.getenv().getOrDefault("PORT", "8080"));
        String jdbcUrl = System.getenv().getOrDefault("DB_URL", "jdbc:sqlite:books.db");
        App app = new App(port, jdbcUrl);
        app.start();
        System.out.println("Book API listening on http://localhost:" + app.port());
        Runtime.getRuntime().addShutdownHook(new Thread(app::stop));
    }
}
