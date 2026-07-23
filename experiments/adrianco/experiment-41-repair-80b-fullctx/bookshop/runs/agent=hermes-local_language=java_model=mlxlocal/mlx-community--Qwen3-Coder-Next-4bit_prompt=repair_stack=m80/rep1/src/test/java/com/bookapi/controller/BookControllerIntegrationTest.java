package com.bookapi.controller;

import com.bookapi.dto.BookRequest;
import com.bookapi.dto.BookResponse;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;
import org.springframework.transaction.annotation.Transactional;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Transactional
public class BookControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;
    private BookRequest validBookRequest;

    @BeforeEach
    void setUp() {
        validBookRequest = new BookRequest();
        validBookRequest.setTitle("Clean Code");
        validBookRequest.setAuthor("Robert C. Martin");
        validBookRequest.setYear(2008);
        validBookRequest.setIsbn("978-0132350884");
    }

    @Test
    void testCreateBook() throws Exception {
        String requestBody = objectMapper.writeValueAsString(validBookRequest);

        mockMvc.perform(MockMvcRequestBuilders.post("/api/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(requestBody))
                .andExpect(status().isCreated())
                .andExpect(header().string("Location", "/api/books/1"))
                .andExpect(jsonPath("$.title").value("Clean Code"))
                .andExpect(jsonPath("$.author").value("Robert C. Martin"))
                .andExpect(jsonPath("$.year").value(2008))
                .andExpect(jsonPath("$.isbn").value("978-0132350884"));
    }

    @Test
    void testCreateBookWithMissingTitle() throws Exception {
        BookRequest request = new BookRequest();
        request.setAuthor("Robert C. Martin");
        request.setYear(2008);
        request.setIsbn("978-0132350884");

        String requestBody = objectMapper.writeValueAsString(request);
        mockMvc.perform(MockMvcRequestBuilders.post("/api/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(requestBody))
                .andExpect(status().isBadRequest());
    }

    @Test
    void testCreateBookWithMissingAuthor() throws Exception {
        BookRequest request = new BookRequest();
        request.setTitle("Clean Code");
        request.setYear(2008);
        request.setIsbn("978-0132350884");

        String requestBody = objectMapper.writeValueAsString(request);
        mockMvc.perform(MockMvcRequestBuilders.post("/api/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(requestBody))
                .andExpect(status().isBadRequest());
    }

    @Test
    void testGetAllBooks() throws Exception {
        // First create a book
        String requestBody = objectMapper.writeValueAsString(validBookRequest);
        mockMvc.perform(MockMvcRequestBuilders.post("/api/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(requestBody))
                .andExpect(status().isCreated());

        // Then get all books
        mockMvc.perform(MockMvcRequestBuilders.get("/api/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(1))
                .andExpect(jsonPath("$[0].title").value("Clean Code"))
                .andExpect(jsonPath("$[0].author").value("Robert C. Martin"));
    }

    @Test
    void testGetAllBooksWithAuthorFilter() throws Exception {
        // Create books with different authors
        BookRequest book1 = new BookRequest();
        book1.setTitle("Clean Code");
        book1.setAuthor("Robert C. Martin");
        book1.setYear(2008);

        BookRequest book2 = new BookRequest();
        book2.setTitle("The Pragmatic Programmer");
        book2.setAuthor("David Thomas");
        book2.setYear(1999);

        BookRequest book3 = new BookRequest();
        book3.setTitle("Clean Architecture");
        book3.setAuthor("Robert C. Martin");
        book3.setYear(2017);

        mockMvc.perform(MockMvcRequestBuilders.post("/api/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(book1)))
                .andExpect(status().isCreated());

        mockMvc.perform(MockMvcRequestBuilders.post("/api/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(book2)))
                .andExpect(status().isCreated());

        mockMvc.perform(MockMvcRequestBuilders.post("/api/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(book3)))
                .andExpect(status().isCreated());

        // Filter by author
        mockMvc.perform(MockMvcRequestBuilders.get("/api/books?author=Robert%20C.%20Martin"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2));
    }

    @Test
    void testGetBookById() throws Exception {
        // First create a book
        String requestBody = objectMapper.writeValueAsString(validBookRequest);
        mockMvc.perform(MockMvcRequestBuilders.post("/api/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(requestBody))
                .andExpect(status().isCreated());

        // Then get the book by ID - use 1 as the first ID
        mockMvc.perform(MockMvcRequestBuilders.get("/api/books/1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("Clean Code"))
                .andExpect(jsonPath("$.author").value("Robert C. Martin"));
    }

    @Test
    void testGetBookByIdNotFound() throws Exception {
        mockMvc.perform(MockMvcRequestBuilders.get("/api/books/999"))
                .andExpect(status().isNotFound());
    }

    @Test
    void testUpdateBook() throws Exception {
        // First create a book
        String requestBody = objectMapper.writeValueAsString(validBookRequest);
        mockMvc.perform(MockMvcRequestBuilders.post("/api/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(requestBody))
                .andExpect(status().isCreated());

        // Update the book
        BookRequest updateRequest = new BookRequest();
        updateRequest.setTitle("Clean Code: A Handbook of Agile Software Craftsmanship");
        updateRequest.setAuthor("Robert C. Martin");
        updateRequest.setYear(2008);
        updateRequest.setIsbn("978-0132350884");

        String updateRequestBody = objectMapper.writeValueAsString(updateRequest);

        mockMvc.perform(MockMvcRequestBuilders.put("/api/books/1")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(updateRequestBody))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("Clean Code: A Handbook of Agile Software Craftsmanship"));
    }

    @Test
    void testUpdateBookNotFound() throws Exception {
        BookRequest updateRequest = new BookRequest();
        updateRequest.setTitle("Updated Title");
        updateRequest.setAuthor("Robert C. Martin");
        updateRequest.setYear(2008);

        String updateRequestBody = objectMapper.writeValueAsString(updateRequest);
        mockMvc.perform(MockMvcRequestBuilders.put("/api/books/999")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(updateRequestBody))
                .andExpect(status().isNotFound());
    }

    @Test
    void testDeleteBook() throws Exception {
        // First create a book
        String requestBody = objectMapper.writeValueAsString(validBookRequest);
        mockMvc.perform(MockMvcRequestBuilders.post("/api/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(requestBody))
                .andExpect(status().isCreated());

        // Then delete the book
        mockMvc.perform(MockMvcRequestBuilders.delete("/api/books/1"))
                .andExpect(status().isNoContent());

        // Verify the book is deleted
        mockMvc.perform(MockMvcRequestBuilders.get("/api/books/1"))
                .andExpect(status().isNotFound());
    }

    @Test
    void testDeleteBookNotFound() throws Exception {
        mockMvc.perform(MockMvcRequestBuilders.delete("/api/books/999"))
                .andExpect(status().isNotFound());
    }

    @Test
    void testHealthCheck() throws Exception {
        mockMvc.perform(MockMvcRequestBuilders.get("/api/books/health"))
                .andExpect(status().isOk())
                .andExpect(content().string("OK"));
    }
}
