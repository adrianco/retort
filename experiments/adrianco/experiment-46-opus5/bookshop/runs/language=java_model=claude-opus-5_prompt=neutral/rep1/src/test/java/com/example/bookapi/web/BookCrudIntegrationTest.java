package com.example.bookapi.web;

import com.example.bookapi.AbstractIntegrationTest;
import com.fasterxml.jackson.databind.JsonNode;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import java.util.LinkedHashMap;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.nullValue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class BookCrudIntegrationTest extends AbstractIntegrationTest {

    @Test
    @DisplayName("POST /books creates a book and returns 201 with a Location header")
    void createReturnsCreatedBook() throws Exception {
        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(book("Dune", "Frank Herbert", 1965, "0-441-17271-7"))))
                .andExpect(status().isCreated())
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
                .andExpect(header().exists("Location"))
                .andExpect(jsonPath("$.id").isNumber())
                .andExpect(jsonPath("$.title").value("Dune"))
                .andExpect(jsonPath("$.author").value("Frank Herbert"))
                .andExpect(jsonPath("$.year").value(1965))
                .andExpect(jsonPath("$.isbn").value("0441172717"))
                .andExpect(jsonPath("$.createdAt").exists());
    }

    @Test
    @DisplayName("The created book survives a round trip through the database")
    void createThenGetById() throws Exception {
        long id = create("Dune", "Frank Herbert", 1965, null);

        mockMvc.perform(get("/books/{id}", id))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value((int) id))
                .andExpect(jsonPath("$.title").value("Dune"))
                .andExpect(jsonPath("$.isbn").value(nullValue()));
    }

    @Test
    @DisplayName("GET /books lists every book")
    void listReturnsAllBooks() throws Exception {
        create("Dune", "Frank Herbert", 1965, null);
        create("Neuromancer", "William Gibson", 1984, null);

        mockMvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(2)))
                .andExpect(jsonPath("$[0].title").value("Dune"))
                .andExpect(jsonPath("$[1].title").value("Neuromancer"));
    }

    @Test
    @DisplayName("GET /books?author= filters case-insensitively")
    void listFiltersByAuthor() throws Exception {
        create("Dune", "Frank Herbert", 1965, null);
        create("Children of Dune", "Frank Herbert", 1976, null);
        create("Neuromancer", "William Gibson", 1984, null);

        mockMvc.perform(get("/books").param("author", "frank herbert"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(2)))
                .andExpect(jsonPath("$[0].author").value("Frank Herbert"))
                .andExpect(jsonPath("$[1].author").value("Frank Herbert"));

        mockMvc.perform(get("/books").param("author", "Nobody"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(0)));
    }

    @Test
    @DisplayName("PUT /books/{id} replaces every mutable field")
    void updateReplacesBook() throws Exception {
        long id = create("Dune", "Frank Herbert", 1965, "0-441-17271-7");

        mockMvc.perform(put("/books/{id}", id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(book("Dune Messiah", "Frank Herbert", 1969, null))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value((int) id))
                .andExpect(jsonPath("$.title").value("Dune Messiah"))
                .andExpect(jsonPath("$.year").value(1969))
                .andExpect(jsonPath("$.isbn").value(nullValue()));

        mockMvc.perform(get("/books/{id}", id))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("Dune Messiah"));
    }

    @Test
    @DisplayName("PUT keeps createdAt and moves updatedAt forward")
    void updatePreservesCreatedAt() throws Exception {
        long id = create("Dune", "Frank Herbert", 1965, null);
        JsonNode before = objectMapper.readTree(
                mockMvc.perform(get("/books/{id}", id)).andReturn().getResponse().getContentAsString());

        JsonNode after = objectMapper.readTree(mockMvc.perform(put("/books/{id}", id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(book("Dune", "Frank Herbert", 1966, null))))
                .andReturn().getResponse().getContentAsString());

        assertThat(after.get("createdAt").asText()).isEqualTo(before.get("createdAt").asText());
        assertThat(after.get("updatedAt").asText()).isNotEqualTo(before.get("updatedAt").asText());
    }

    @Test
    @DisplayName("DELETE /books/{id} returns 204 and the book is gone")
    void deleteRemovesBook() throws Exception {
        long id = create("Dune", "Frank Herbert", 1965, null);

        mockMvc.perform(delete("/books/{id}", id)).andExpect(status().isNoContent());
        mockMvc.perform(get("/books/{id}", id)).andExpect(status().isNotFound());
        mockMvc.perform(get("/books")).andExpect(jsonPath("$", hasSize(0)));
    }

    @Test
    @DisplayName("Unknown ids yield 404 with a JSON error body on GET, PUT and DELETE")
    void unknownIdsReturnNotFound() throws Exception {
        mockMvc.perform(get("/books/{id}", 4242))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.status").value(404))
                .andExpect(jsonPath("$.message").value("Book 4242 not found"));

        mockMvc.perform(put("/books/{id}", 4242)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(book("Dune", "Frank Herbert", 1965, null))))
                .andExpect(status().isNotFound());

        mockMvc.perform(delete("/books/{id}", 4242))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.status").value(404));
    }

    @Test
    @DisplayName("A non-numeric id is rejected with 400 rather than 500")
    void nonNumericIdIsBadRequest() throws Exception {
        mockMvc.perform(get("/books/{id}", "abc"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.status").value(400));
    }

    private long create(String title, String author, Integer year, String isbn) throws Exception {
        String body = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(book(title, author, year, isbn))))
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString();
        return objectMapper.readTree(body).get("id").asLong();
    }

    private Map<String, Object> book(String title, String author, Integer year, String isbn) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("title", title);
        payload.put("author", author);
        payload.put("year", year);
        payload.put("isbn", isbn);
        return payload;
    }
}
