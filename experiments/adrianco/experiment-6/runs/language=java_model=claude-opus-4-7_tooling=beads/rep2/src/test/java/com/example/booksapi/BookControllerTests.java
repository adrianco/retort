package com.example.booksapi;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import java.util.Map;

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class BookControllerTests {

    @Autowired private MockMvc mvc;
    @Autowired private BookRepository repository;
    @Autowired private ObjectMapper objectMapper;

    @BeforeEach
    void clean() {
        repository.deleteAll();
    }

    @Test
    void healthEndpointReturnsOk() throws Exception {
        mvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("ok"));
    }

    @Test
    void createBookReturns201AndPersists() throws Exception {
        String body = objectMapper.writeValueAsString(
                Map.of("title", "Dune", "author", "Herbert", "year", 1965, "isbn", "978-0-441-17271-9"));

        MvcResult result = mvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").exists())
                .andExpect(jsonPath("$.title").value("Dune"))
                .andExpect(jsonPath("$.author").value("Herbert"))
                .andReturn();

        Long id = objectMapper.readTree(result.getResponse().getContentAsString()).get("id").asLong();

        mvc.perform(get("/books/" + id))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("Dune"));
    }

    @Test
    void createBookWithoutTitleReturns400() throws Exception {
        String body = objectMapper.writeValueAsString(Map.of("author", "Herbert"));
        mvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fields.title").exists());
    }

    @Test
    void listBooksFiltersByAuthor() throws Exception {
        repository.save(new Book("A", "Alice", 2001, "isbn1"));
        repository.save(new Book("B", "Bob", 2002, "isbn2"));
        repository.save(new Book("C", "Alice", 2003, "isbn3"));

        mvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(3)));

        mvc.perform(get("/books").param("author", "Alice"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(2)));
    }

    @Test
    void updateBookChangesFields() throws Exception {
        Book existing = repository.save(new Book("Old", "Author", 2000, "isbn"));
        String body = objectMapper.writeValueAsString(
                Map.of("title", "New", "author", "Author2", "year", 2024, "isbn", "isbn-new"));

        mvc.perform(put("/books/" + existing.getId())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("New"))
                .andExpect(jsonPath("$.author").value("Author2"));
    }

    @Test
    void deleteBookRemovesIt() throws Exception {
        Book existing = repository.save(new Book("Delete Me", "Author", 2000, "isbn"));

        mvc.perform(delete("/books/" + existing.getId()))
                .andExpect(status().isNoContent());

        mvc.perform(get("/books/" + existing.getId()))
                .andExpect(status().isNotFound());
    }

    @Test
    void getMissingBookReturns404() throws Exception {
        mvc.perform(get("/books/99999"))
                .andExpect(status().isNotFound());
    }
}
