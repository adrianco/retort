package com.example.bookapi;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import java.nio.file.Path;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Integration tests for the book API endpoints.
 * Runs the full Spring stack against a real (temporary) SQLite database.
 */
@SpringBootTest
@AutoConfigureMockMvc
class BookApiIntegrationTest {

    @DynamicPropertySource
    static void dbProperties(DynamicPropertyRegistry registry) {
        Path dbFile = Path.of("target", "test-books.db");
        registry.add("spring.datasource.url", () -> "jdbc:sqlite:" + dbFile.toAbsolutePath());
    }

    @Autowired
    private MockMvc mvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private JdbcTemplate jdbc;

    /** Each test starts from an empty table so counts are deterministic. */
    @BeforeEach
    void cleanTable() {
        jdbc.execute("DELETE FROM books");
    }

    @Test
    void healthEndpointReturnsOk() throws Exception {
        mvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("ok"))
                .andExpect(header().string("Content-Type",
                        org.hamcrest.Matchers.containsString("application/json")));
    }

    @Test
    void createBookReturns201WithFullBook() throws Exception {
        String body = """
                {"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "isbn": "978-0547928227"}
                """;
        MvcResult result = mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isCreated())
                .andExpect(header().exists("Location"))
                .andExpect(jsonPath("$.id").isNumber())
                .andExpect(jsonPath("$.title").value("The Hobbit"))
                .andExpect(jsonPath("$.author").value("J.R.R. Tolkien"))
                .andExpect(jsonPath("$.year").value(1937))
                .andExpect(jsonPath("$.isbn").value("978-0547928227"))
                .andReturn();

        JsonNode node = objectMapper.readTree(result.getResponse().getContentAsString());
        long id = node.get("id").asLong();
        assertThat(id).isPositive();

        // The created book is retrievable by its id.
        mvc.perform(get("/books/" + id))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("The Hobbit"));
    }

    @Test
    void createBookWithOptionalFieldsOmitted() throws Exception {
        String body = """
                {"title": "Minimal Book", "author": "Someone"}
                """;
        mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.title").value("Minimal Book"))
                .andExpect(jsonPath("$.year").isEmpty())
                .andExpect(jsonPath("$.isbn").isEmpty());
    }

    @Test
    void createBookRejectsMissingTitle() throws Exception {
        String body = """
                {"author": "No Title Author"}
                """;
        mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error").exists());
    }

    @Test
    void createBookRejectsMissingAuthor() throws Exception {
        String body = """
                {"title": "No Author Book"}
                """;
        mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error").exists());
    }

    @Test
    void createBookRejectsBlankTitle() throws Exception {
        String body = """
                {"title": "   ", "author": "Blank Title Author"}
                """;
        mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error").value(org.hamcrest.Matchers.containsString("title")));
    }

    @Test
    void createBookRejectsMalformedJson() throws Exception {
        mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content("{not json"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error").exists());
    }

    @Test
    void listBooksReturnsAllBooks() throws Exception {
        createViaApi("List Book One", "Author A");
        createViaApi("List Book Two", "Author B");
        createViaApi("List Book Three", "Author A");

        mvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(3))
                .andExpect(jsonPath("$[0].title").value("List Book One"))
                .andExpect(jsonPath("$[1].title").value("List Book Two"))
                .andExpect(jsonPath("$[2].title").value("List Book Three"));
    }

    @Test
    void listBooksFiltersByAuthor() throws Exception {
        createViaApi("Filter Book A", "Filter Author");
        createViaApi("Filter Book B", "Other Author");
        createViaApi("Filter Book C", "Filter Author");

        mvc.perform(get("/books").param("author", "Filter Author"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2))
                .andExpect(jsonPath("$[0].title").value("Filter Book A"))
                .andExpect(jsonPath("$[1].title").value("Filter Book C"));
    }

    @Test
    void listBooksWithUnknownAuthorReturnsEmptyList() throws Exception {
        createViaApi("Author List Book", "Present Author");

        mvc.perform(get("/books").param("author", "Nobody Known"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(0));
    }

    @Test
    void getBookByIdReturnsBook() throws Exception {
        long id = createViaApi("Single Book", "Single Author");

        mvc.perform(get("/books/" + id))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(id))
                .andExpect(jsonPath("$.title").value("Single Book"))
                .andExpect(jsonPath("$.author").value("Single Author"));
    }

    @Test
    void getUnknownBookReturns404() throws Exception {
        mvc.perform(get("/books/999999"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error").exists());
    }

    @Test
    void getBookWithNonNumericIdReturns400() throws Exception {
        mvc.perform(get("/books/not-a-number"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error").value(org.hamcrest.Matchers.containsString("not-a-number")));
    }

    @Test
    void updateBookReplacesFields() throws Exception {
        long id = createViaApi("Old Title", "Old Author");

        String body = """
                {"title": "New Title", "author": "New Author", "year": 2020, "isbn": "978-0-00"}
                """;
        mvc.perform(put("/books/" + id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(id))
                .andExpect(jsonPath("$.title").value("New Title"))
                .andExpect(jsonPath("$.author").value("New Author"))
                .andExpect(jsonPath("$.year").value(2020))
                .andExpect(jsonPath("$.isbn").value("978-0-00"));

        // Persisted change is visible on a fresh GET.
        mvc.perform(get("/books/" + id))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("New Title"));
    }

    @Test
    void updateUnknownBookReturns404() throws Exception {
        String body = """
                {"title": "Ghost", "author": "Nowhere"}
                """;
        mvc.perform(put("/books/999999")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error").exists());
    }

    @Test
    void updateBookRejectsMissingAuthor() throws Exception {
        long id = createViaApi("Update Target", "Original Author");

        String body = """
                {"title": "Updated Title"}
                """;
        mvc.perform(put("/books/" + id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error").exists());

        // Original book is untouched.
        mvc.perform(get("/books/" + id))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("Update Target"))
                .andExpect(jsonPath("$.author").value("Original Author"));
    }

    @Test
    void deleteBookRemovesIt() throws Exception {
        long id = createViaApi("Doomed Book", "Doomed Author");

        mvc.perform(delete("/books/" + id))
                .andExpect(status().isNoContent());

        mvc.perform(get("/books/" + id))
                .andExpect(status().isNotFound());
    }

    @Test
    void deleteUnknownBookReturns404() throws Exception {
        mvc.perform(delete("/books/999999"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error").exists());
    }

    @Test
    void unknownRouteReturns404() throws Exception {
        mvc.perform(get("/no-such-route"))
                .andExpect(status().isNotFound());
    }

    /**
     * Helper: creates a book through the API and returns its id.
     */
    private long createViaApi(String title, String author) throws Exception {
        String body = objectMapper.writeValueAsString(Map.of("title", title, "author", author));
        MvcResult result = mvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isCreated())
                .andReturn();
        return objectMapper.readTree(result.getResponse().getContentAsString()).get("id").asLong();
    }
}
