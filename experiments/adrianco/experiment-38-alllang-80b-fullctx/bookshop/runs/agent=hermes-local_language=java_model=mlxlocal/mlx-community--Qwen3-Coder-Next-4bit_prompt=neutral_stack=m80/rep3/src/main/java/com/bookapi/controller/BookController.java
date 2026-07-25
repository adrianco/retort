package com.bookapi.controller;

import com.bookapi.model.Book;
import com.bookapi.repository.BookRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;
import java.util.Optional;

import static spark.Spark.*;

public class BookController {
    private static final Logger logger = LoggerFactory.getLogger(BookController.class);
    private static final ObjectMapper objectMapper = new ObjectMapper();
    private final BookRepository bookRepository;

    public BookController() {
        this.bookRepository = new BookRepository();
        setupRoutes();
    }

    private void setupRoutes() {
        // Health check
        get("/health", (req, res) -> {
            res.status(200);
            return objectMapper.writeValueAsString("{\"status\": \"healthy\"}");
        });

        // List all books
        get("/books", (req, res) -> {
            String author = req.queryParams("author");
            List<Book> books = bookRepository.findAll(author);
            res.status(200);
            return objectMapper.writeValueAsString(books);
        });

        // Get single book
        get("/books/:id", (req, res) -> {
            int id = Integer.parseInt(req.params("id"));
            Optional<Book> book = bookRepository.findById(id);
            if (book.isPresent()) {
                res.status(200);
                return objectMapper.writeValueAsString(book.get());
            } else {
                res.status(404);
                return objectMapper.writeValueAsString("{\"error\": \"Book not found\"}");
            }
        });

        // Create book
        post("/books", (req, res) -> {
            try {
                Book book = objectMapper.readValue(req.body(), Book.class);
                Book savedBook = bookRepository.save(book);
                if (savedBook != null) {
                    res.status(201);
                    res.header("Location", "/books/" + savedBook.getId());
                    return objectMapper.writeValueAsString(savedBook);
                } else {
                    res.status(500);
                    return objectMapper.writeValueAsString("{\"error\": \"Failed to create book\"}");
                }
            } catch (Exception e) {
                logger.error("Error creating book", e);
                res.status(400);
                return objectMapper.writeValueAsString("{\"error\": \"Invalid request body\"}");
            }
        });

        // Update book
        put("/books/:id", (req, res) -> {
            try {
                int id = Integer.parseInt(req.params("id"));
                Optional<Book> existingBook = bookRepository.findById(id);
                if (!existingBook.isPresent()) {
                    res.status(404);
                    return objectMapper.writeValueAsString("{\"error\": \"Book not found\"}");
                }
                
                Book book = objectMapper.readValue(req.body(), Book.class);
                book.setId(id);
                Book updatedBook = bookRepository.save(book);
                
                res.status(200);
                return objectMapper.writeValueAsString(updatedBook);
            } catch (Exception e) {
                logger.error("Error updating book", e);
                res.status(400);
                return objectMapper.writeValueAsString("{\"error\": \"Invalid request body\"}");
            }
        });

        // Delete book
        delete("/books/:id", (req, res) -> {
            int id = Integer.parseInt(req.params("id"));
            boolean deleted = bookRepository.delete(id);
            if (deleted) {
                res.status(204);
            } else {
                res.status(404);
                return objectMapper.writeValueAsString("{\"error\": \"Book not found\"}");
            }
            return "";
        });
    }
}
