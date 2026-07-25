package com.example;

import com.example.model.Book;
import com.example.repository.BookRepository;
import com.example.service.BookService;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.ServletConfig;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.eclipse.jetty.server.Server;
import org.eclipse.jetty.servlet.ServletContextHandler;
import org.eclipse.jetty.servlet.ServletHolder;

import java.io.IOException;
import java.util.Optional;

public class BookApiApplication {
    private static BookService bookService;
    private static ObjectMapper objectMapper;

    public static void main(String[] args) throws Exception {
        objectMapper = new ObjectMapper();
        BookRepository bookRepository = new BookRepository();
        bookRepository.init();
        bookService = new BookService(bookRepository);

        Server server = new Server(8080);
        
        ServletContextHandler context = new ServletContextHandler();
        context.setContextPath("/");
        context.addServlet(new ServletHolder("api", new BookApiServlet()), "/*");
        
        server.setHandler(context);
        
        System.out.println("Starting Book API Server on port 8080...");
        server.start();
        server.join();
    }

    public static class BookApiServlet extends HttpServlet {
        @Override
        public void init(ServletConfig config) throws ServletException {
            super.init(config);
            BookRepository bookRepository = new BookRepository();
            bookRepository.init();
            bookService = new BookService(bookRepository);
            objectMapper = new ObjectMapper();
        }

        @Override
        protected void doGet(HttpServletRequest req, HttpServletResponse resp) 
                throws ServletException, IOException {
            resp.setContentType("application/json");
            resp.setCharacterEncoding("UTF-8");

            String path = req.getPathInfo();
            
            if (path == null || path.equals("/") || path.equals("/health")) {
                resp.setStatus(HttpServletResponse.SC_OK);
                resp.getWriter().write(objectMapper.writeValueAsString(
                    java.util.Map.of("status", "healthy", "service", "Book API")));
                return;
            }

            String[] parts = path.split("/");
            if (parts.length >= 2 && parts[1].equals("books")) {
                String authorFilter = req.getParameter("author");
                
                if (parts.length == 2) {
                    // GET /books - list all books
                    if (authorFilter != null) {
                        resp.setStatus(HttpServletResponse.SC_OK);
                        resp.getWriter().write(objectMapper.writeValueAsString(
                            bookService.findBooksByAuthor(authorFilter)));
                    } else {
                        resp.setStatus(HttpServletResponse.SC_OK);
                        resp.getWriter().write(objectMapper.writeValueAsString(
                            bookService.getAllBooks()));
                    }
                } else if (parts.length == 3) {
                    // GET /books/{id}
                    try {
                        Long id = Long.parseLong(parts[2]);
                        Optional<Book> book = bookService.getBookById(id);
                        if (book.isPresent()) {
                            resp.setStatus(HttpServletResponse.SC_OK);
                            resp.getWriter().write(objectMapper.writeValueAsString(book.get()));
                        } else {
                            resp.setStatus(HttpServletResponse.SC_NOT_FOUND);
                            resp.getWriter().write(objectMapper.writeValueAsString(
                                java.util.Map.of("error", "Book not found")));
                        }
                    } catch (NumberFormatException e) {
                        resp.setStatus(HttpServletResponse.SC_BAD_REQUEST);
                        resp.getWriter().write(objectMapper.writeValueAsString(
                            java.util.Map.of("error", "Invalid book ID format")));
                    }
                }
            }
        }

        @Override
        protected void doPost(HttpServletRequest req, HttpServletResponse resp) 
                throws ServletException, IOException {
            resp.setContentType("application/json");
            resp.setCharacterEncoding("UTF-8");

            String path = req.getPathInfo();
            if (path != null && path.equals("/books")) {
                try {
                    Book book = objectMapper.readValue(req.getInputStream(), Book.class);
                    Book savedBook = bookService.createBook(book);
                    resp.setStatus(HttpServletResponse.SC_CREATED);
                    resp.getWriter().write(objectMapper.writeValueAsString(savedBook));
                } catch (IllegalArgumentException e) {
                    resp.setStatus(HttpServletResponse.SC_BAD_REQUEST);
                    resp.getWriter().write(objectMapper.writeValueAsString(
                        java.util.Map.of("error", e.getMessage())));
                } catch (Exception e) {
                    resp.setStatus(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
                    resp.getWriter().write(objectMapper.writeValueAsString(
                        java.util.Map.of("error", e.getMessage())));
                }
            }
        }

        @Override
        protected void doPut(HttpServletRequest req, HttpServletResponse resp) 
                throws ServletException, IOException {
            resp.setContentType("application/json");
            resp.setCharacterEncoding("UTF-8");

            String path = req.getPathInfo();
            String[] parts = path.split("/");
            
            if (parts.length >= 2 && parts[1].equals("books") && parts.length == 3) {
                try {
                    Long id = Long.parseLong(parts[2]);
                    Book book = objectMapper.readValue(req.getInputStream(), Book.class);
                    book.setId(id);
                    Optional<Book> updatedBook = bookService.updateBook(book);
                    if (updatedBook.isPresent()) {
                        resp.setStatus(HttpServletResponse.SC_OK);
                        resp.getWriter().write(objectMapper.writeValueAsString(updatedBook.get()));
                    } else {
                        resp.setStatus(HttpServletResponse.SC_NOT_FOUND);
                        resp.getWriter().write(objectMapper.writeValueAsString(
                            java.util.Map.of("error", "Book not found")));
                    }
                } catch (NumberFormatException e) {
                    resp.setStatus(HttpServletResponse.SC_BAD_REQUEST);
                    resp.getWriter().write(objectMapper.writeValueAsString(
                        java.util.Map.of("error", "Invalid book ID format")));
                } catch (IllegalArgumentException e) {
                    resp.setStatus(HttpServletResponse.SC_BAD_REQUEST);
                    resp.getWriter().write(objectMapper.writeValueAsString(
                        java.util.Map.of("error", e.getMessage())));
                } catch (Exception e) {
                    resp.setStatus(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
                    resp.getWriter().write(objectMapper.writeValueAsString(
                        java.util.Map.of("error", e.getMessage())));
                }
            }
        }

        @Override
        protected void doDelete(HttpServletRequest req, HttpServletResponse resp) 
                throws ServletException, IOException {
            resp.setContentType("application/json");
            resp.setCharacterEncoding("UTF-8");

            String path = req.getPathInfo();
            String[] parts = path.split("/");
            
            if (parts.length >= 2 && parts[1].equals("books") && parts.length == 3) {
                try {
                    Long id = Long.parseLong(parts[2]);
                    boolean deleted = bookService.deleteBook(id);
                    if (deleted) {
                        resp.setStatus(HttpServletResponse.SC_OK);
                        resp.getWriter().write(objectMapper.writeValueAsString(
                            java.util.Map.of("message", "Book deleted successfully")));
                    } else {
                        resp.setStatus(HttpServletResponse.SC_NOT_FOUND);
                        resp.getWriter().write(objectMapper.writeValueAsString(
                            java.util.Map.of("error", "Book not found")));
                    }
                } catch (NumberFormatException e) {
                    resp.setStatus(HttpServletResponse.SC_BAD_REQUEST);
                    resp.getWriter().write(objectMapper.writeValueAsString(
                        java.util.Map.of("error", "Invalid book ID format")));
                }
            }
        }
    }
}
