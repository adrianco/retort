package com.bookapi.integration;

import com.bookapi.model.Book;
import com.fasterxml.jackson.databind.ObjectMapper;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import org.junit.jupiter.api.*;

import java.io.IOException;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Integration tests for the Book API.
 * These tests require the server to be running on port 4567.
 * 
 * To run these tests, start the server first:
 *   ./gradlew run
 * 
 * Then in another terminal:
 *   ./gradlew test --tests BookApiIntegrationTest
 */
public class BookApiIntegrationTest {
    
    private static final ObjectMapper objectMapper = new ObjectMapper();
    private static final OkHttpClient httpClient = new OkHttpClient();
    private static final String BASE_URL = System.getProperty("api.url", "http://localhost:4567");

    @Test
    void testHealthCheck() throws IOException {
        // When
        String response = get("/health");
        
        // Then
        assertNotNull(response);
        assertTrue(response.contains("\"status\":\"healthy\""));
    }

    @Test
    void testCreateBook() throws IOException {
        // Given
        Book book = new Book("Test Book", "Test Author", 2024, "ISBN123");
        String json = objectMapper.writeValueAsString(book);
        
        // When
        String response = post("/books", json);
        
        // Then
        assertNotNull(response);
        Book createdBook = objectMapper.readValue(response, Book.class);
        assertNotNull(createdBook.getId());
        assertEquals("Test Book", createdBook.getTitle());
        assertEquals("Test Author", createdBook.getAuthor());
        assertEquals(2024, createdBook.getYear());
        assertEquals("ISBN123", createdBook.getIsbn());
    }

    @Test
    void testGetAllBooks() throws IOException {
        // Given
        createBook("Book 1", "Author A", 2020, "ISBN1");
        createBook("Book 2", "Author B", 2021, "ISBN2");
        
        // When
        String response = get("/books");
        
        // Then
        assertNotNull(response);
        @SuppressWarnings("unchecked")
        List<Book> books = objectMapper.readValue(response, List.class);
        assertEquals(2, books.size());
    }

    @Test
    void testGetBookById() throws IOException {
        // Given
        Book created = createBook("Find This Book", "Author", 2024, "ISBN123");
        
        // When
        String response = get("/books/" + created.getId());
        
        // Then
        assertNotNull(response);
        Book foundBook = objectMapper.readValue(response, Book.class);
        assertEquals(created.getId(), foundBook.getId());
        assertEquals("Find This Book", foundBook.getTitle());
    }

    @Test
    void testGetBookByIdNotFound() throws IOException {
        // When
        Response resp = executeRequest(new Request.Builder()
            .get()
            .url(BASE_URL + "/books/999999")
            .build());
        
        // Then
        assertEquals(404, resp.code());
        resp.close();
    }

    @Test
    void testUpdateBook() throws IOException {
        // Given
        Book created = createBook("Original Title", "Original Author", 2020, "OriginalISBN");
        
        // When
        created.setTitle("Updated Title");
        created.setAuthor("Updated Author");
        created.setYear(2024);
        created.setIsbn("UpdatedISBN");
        String json = objectMapper.writeValueAsString(created);
        String response = put("/books/" + created.getId(), json);
        
        // Then
        assertNotNull(response);
        Book updatedBook = objectMapper.readValue(response, Book.class);
        assertEquals("Updated Title", updatedBook.getTitle());
        assertEquals("Updated Author", updatedBook.getAuthor());
        assertEquals(2024, updatedBook.getYear());
        assertEquals("UpdatedISBN", updatedBook.getIsbn());
    }

    @Test
    void testUpdateBookNotFound() throws IOException {
        // Given
        Book book = new Book("Test", "Author", 2024, "ISBN123");
        String json = objectMapper.writeValueAsString(book);
        
        // When
        Response resp = executeRequest(new Request.Builder()
            .put(RequestBody.create(json, MediaType.parse("application/json")))
            .url(BASE_URL + "/books/999999")
            .build());
        
        // Then
        assertEquals(404, resp.code());
        resp.close();
    }

    @Test
    void testDeleteBook() throws IOException {
        // Given
        Book created = createBook("Delete Me", "Author", 2024, "ISBN123");
        
        // When
        Response resp = executeRequest(new Request.Builder()
            .delete()
            .url(BASE_URL + "/books/" + created.getId())
            .build());
        
        // Then
        assertEquals(204, resp.code());
        resp.close();
        
        // Verify book is deleted
        Response getResp = executeRequest(new Request.Builder()
            .get()
            .url(BASE_URL + "/books/" + created.getId())
            .build());
        assertEquals(404, getResp.code());
        getResp.close();
    }

    @Test
    void testDeleteBookNotFound() throws IOException {
        // When
        Response resp = executeRequest(new Request.Builder()
            .delete()
            .url(BASE_URL + "/books/999999")
            .build());
        
        // Then
        assertEquals(404, resp.code());
        resp.close();
    }

    @Test
    void testFilterBooksByAuthor() throws IOException {
        // Given
        createBook("Book 1", "Author A", 2020, "ISBN1");
        createBook("Book 2", "Author B", 2021, "ISBN2");
        createBook("Book 3", "Author A", 2022, "ISBN3");
        
        // When
        String response = get("/books?author=Author A");
        
        // Then
        assertNotNull(response);
        @SuppressWarnings("unchecked")
        List<Book> books = objectMapper.readValue(response, List.class);
        assertEquals(2, books.size());
        assertTrue(books.stream().allMatch(b -> b.getAuthor().equals("Author A")));
    }

    private Book createBook(String title, String author, int year, String isbn) throws IOException {
        Book book = new Book(title, author, year, isbn);
        String json = objectMapper.writeValueAsString(book);
        String response = post("/books", json);
        return objectMapper.readValue(response, Book.class);
    }

    private String get(String endpoint) throws IOException {
        Response resp = executeRequest(new Request.Builder().get().url(BASE_URL + endpoint).build());
        String body = resp.body().string();
        resp.close();
        return body;
    }

    private String post(String endpoint, String json) throws IOException {
        RequestBody body = RequestBody.create(json, MediaType.parse("application/json"));
        Response resp = executeRequest(new Request.Builder().post(body).url(BASE_URL + endpoint).build());
        String response = resp.body().string();
        resp.close();
        return response;
    }

    private String put(String endpoint, String json) throws IOException {
        RequestBody body = RequestBody.create(json, MediaType.parse("application/json"));
        Response resp = executeRequest(new Request.Builder().put(body).url(BASE_URL + endpoint).build());
        String response = resp.body().string();
        resp.close();
        return response;
    }

    private String delete(String endpoint) throws IOException {
        Response resp = executeRequest(new Request.Builder().delete().url(BASE_URL + endpoint).build());
        String response = resp.body().string();
        resp.close();
        return response;
    }

    private Response executeRequest(Request request) throws IOException {
        return httpClient.newCall(request).execute();
    }
}
