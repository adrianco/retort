package com.example.books;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class BookApiIntegrationTest {
    @Autowired MockMvc mvc;
    @Autowired JdbcTemplate jdbc;

    @BeforeEach
    void clearBooks() { jdbc.update("DELETE FROM books"); }

    @Test
    void createsAndReadsBook() throws Exception {
        mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\":\"Dune\",\"author\":\"Frank Herbert\",\"year\":1965,\"isbn\":\"9780441013593\"}"))
                .andExpect(status().isCreated()).andExpect(jsonPath("$.id").isNumber())
                .andExpect(jsonPath("$.title").value("Dune"));
        mvc.perform(get("/books")).andExpect(status().isOk()).andExpect(jsonPath("$", hasSize(1)));
    }

    @Test
    void validatesRequiredTitleAndAuthor() throws Exception {
        mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\":\"  \",\"author\":\"\"}"))
                .andExpect(status().isBadRequest()).andExpect(jsonPath("$.error").exists());
    }

    @Test
    void filtersUpdatesAndDeletesBooks() throws Exception {
        long id = create("Dune", "Frank Herbert");
        create("Foundation", "Isaac Asimov");
        mvc.perform(get("/books").param("author", "Frank Herbert"))
                .andExpect(status().isOk()).andExpect(jsonPath("$", hasSize(1)));
        mvc.perform(put("/books/" + id).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\":\"Dune Messiah\",\"author\":\"Frank Herbert\"}"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.title").value("Dune Messiah"));
        mvc.perform(delete("/books/" + id)).andExpect(status().isNoContent());
        mvc.perform(get("/books/" + id)).andExpect(status().isNotFound());
    }

    @Test
    void healthCheckIsAvailable() throws Exception {
        mvc.perform(get("/health")).andExpect(status().isOk()).andExpect(jsonPath("$.status").value("ok"));
    }

    private long create(String title, String author) throws Exception {
        String response = mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\":\"" + title + "\",\"author\":\"" + author + "\"}"))
                .andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
        return new com.fasterxml.jackson.databind.ObjectMapper().readTree(response).get("id").asLong();
    }
}
