package com.example.bookapi;

import com.example.bookapi.entity.Book;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class BookControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void testHealthEndpoint() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("healthy"));
    }

    @Test
    void testCreateBook() throws Exception {
        Book book = new Book();
        book.setTitle("The Great Gatsby");
        book.setAuthor("F. Scott Fitzgerald");
        book.setYear(1925);
        book.setIsbn("978-0743273565");

        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(book)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.title").value("The Great Gatsby"))
                .andExpect(jsonPath("$.author").value("F. Scott Fitzgerald"))
                .andExpect(jsonPath("$.year").value(1925))
                .andExpect(jsonPath("$.isbn").value("978-0743273565"));
    }

    @Test
    void testCreateBookValidationMissingTitle() throws Exception {
        Book book = new Book();
        book.setAuthor("Some Author");
        book.setYear(2020);
        book.setIsbn("123-456");

        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(book)))
                .andExpect(status().isBadRequest());
    }

    @Test
    void testCreateBookValidationMissingAuthor() throws Exception {
        Book book = new Book();
        book.setTitle("Some Book");
        book.setYear(2020);
        book.setIsbn("123-456");

        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(book)))
                .andExpect(status().isBadRequest());
    }

    @Test
    void testGetAllBooks() throws Exception {
        // First create a book
        Book book = new Book();
        book.setTitle("1984");
        book.setAuthor("George Orwell");
        book.setYear(1949);
        book.setIsbn("978-0451524935");

        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(book)))
                .andExpect(status().isCreated());

        // Then list all books
        mockMvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].title").value("1984"))
                .andExpect(jsonPath("$[0].author").value("George Orwell"));
    }

    @Test
    void testGetBooksByAuthorFilter() throws Exception {
        // Create a book by a specific author
        Book book = new Book();
        book.setTitle("Brave New World");
        book.setAuthor("Aldous Huxley");
        book.setYear(1932);
        book.setIsbn("978-0060850524");

        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(book)))
                .andExpect(status().isCreated());

        // Filter by author
        mockMvc.perform(get("/books").param("author", "Aldous Huxley"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].title").value("Brave New World"));
    }

    @Test
    void testGetBookById() throws Exception {
        // Create a book first
        Book book = new Book();
        book.setTitle("To Kill a Mockingbird");
        book.setAuthor("Harper Lee");
        book.setYear(1960);
        book.setIsbn("978-0061120084");

        String createResponse = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(book)))
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString();

        // Extract id from response
        String id = objectMapper.readTree(createResponse).get("id").asText();

        // Get the book by id
        mockMvc.perform(get("/books/" + id))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("To Kill a Mockingbird"));
    }

    @Test
    void testGetBookByIdNotFound() throws Exception {
        mockMvc.perform(get("/books/99999"))
                .andExpect(status().isNotFound());
    }

    @Test
    void testUpdateBook() throws Exception {
        // Create a book first
        Book book = new Book();
        book.setTitle("Original Title");
        book.setAuthor("Original Author");
        book.setYear(2000);
        book.setIsbn("000-0000000000");

        String createResponse = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(book)))
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString();

        String id = objectMapper.readTree(createResponse).get("id").asText();

        // Update the book
        Book updatedBook = new Book();
        updatedBook.setTitle("Updated Title");
        updatedBook.setAuthor("Updated Author");
        updatedBook.setYear(2024);
        updatedBook.setIsbn("000-0000000001");

        mockMvc.perform(put("/books/" + id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(updatedBook)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("Updated Title"))
                .andExpect(jsonPath("$.author").value("Updated Author"));
    }

    @Test
    void testDeleteBook() throws Exception {
        // Create a book first
        Book book = new Book();
        book.setTitle("Book to Delete");
        book.setAuthor("Author");
        book.setYear(2020);
        book.setIsbn("000-0000000002");

        String createResponse = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(book)))
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString();

        String id = objectMapper.readTree(createResponse).get("id").asText();

        // Delete the book
        mockMvc.perform(delete("/books/" + id))
                .andExpect(status().isNoContent());

        // Verify it's deleted
        mockMvc.perform(get("/books/" + id))
                .andExpect(status().isNotFound());
    }
}
