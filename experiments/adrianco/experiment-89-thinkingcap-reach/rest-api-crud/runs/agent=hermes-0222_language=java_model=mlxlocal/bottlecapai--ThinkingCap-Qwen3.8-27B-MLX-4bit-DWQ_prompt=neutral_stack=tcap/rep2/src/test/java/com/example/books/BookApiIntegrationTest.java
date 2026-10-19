package com.example.books;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class BookApiIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    private long createBook(String title, String author, Integer year, String isbn) throws Exception {
        Book book = new Book(null, title, author, year, isbn);
        MvcResult result = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(book)))
                .andExpect(status().isCreated())
                .andReturn();
        JsonNode body = objectMapper.readTree(result.getResponse().getContentAsString());
        return body.get("id").asLong();
    }

    @Test
    void healthEndpointReturnsOk() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("ok"));
    }

    @Test
    void createBookReturns201WithIdAndFields() throws Exception {
        String json = """
                {"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "isbn": "978-0547928227"}
                """;
        mockMvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content(json))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").isNumber())
                .andExpect(jsonPath("$.title").value("The Hobbit"))
                .andExpect(jsonPath("$.author").value("J.R.R. Tolkien"))
                .andExpect(jsonPath("$.year").value(1937))
                .andExpect(jsonPath("$.isbn").value("978-0547928227"));
    }

    @Test
    void createBookWithoutTitleReturns400() throws Exception {
        mockMvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"author\": \"Some Author\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error").isNotEmpty());
    }

    @Test
    void createBookWithoutAuthorReturns400() throws Exception {
        mockMvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\": \"Some Title\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error").isNotEmpty());
    }

    @Test
    void createBookWithMalformedJsonReturns400() throws Exception {
        mockMvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content("{not json"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void getBookByIdReturnsBook() throws Exception {
        long id = createBook("Dune", "Frank Herbert", 1965, "978-0441172719");
        mockMvc.perform(get("/books/" + id))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(id))
                .andExpect(jsonPath("$.title").value("Dune"))
                .andExpect(jsonPath("$.author").value("Frank Herbert"));
    }

    @Test
    void getBookByIdNotFoundReturns404() throws Exception {
        mockMvc.perform(get("/books/999999999"))
                .andExpect(status().isNotFound());
    }

    @Test
    void listBooksReturnsAllAndSupportsAuthorFilter() throws Exception {
        String uniqueAuthor = "Unique Author " + System.nanoTime();
        createBook("Alpha Book", uniqueAuthor, 2000, null);
        createBook("Beta Book", uniqueAuthor, 2001, null);
        createBook("Gamma Book", "Other Author " + System.nanoTime(), 2002, null);

        MvcResult all = mockMvc.perform(get("/books")).andExpect(status().isOk()).andReturn();
        JsonNode allBody = objectMapper.readTree(all.getResponse().getContentAsString());
        int matchesAll = 0;
        for (JsonNode node : allBody) {
            if (uniqueAuthor.equals(node.get("author").asText())) {
                matchesAll++;
            }
        }
        assertThat(matchesAll).isEqualTo(2);

        MvcResult filtered = mockMvc.perform(get("/books").param("author", uniqueAuthor))
                .andExpect(status().isOk()).andReturn();
        JsonNode filteredBody = objectMapper.readTree(filtered.getResponse().getContentAsString());
        assertThat(filteredBody.size()).isEqualTo(2);
        for (JsonNode node : filteredBody) {
            assertThat(node.get("author").asText()).isEqualTo(uniqueAuthor);
        }
    }

    @Test
    void updateBookReturns200WithUpdatedFields() throws Exception {
        long id = createBook("Old Title", "Old Author", 1999, null);
        String json = """
                {"title": "New Title", "author": "New Author", "year": 2020, "isbn": "978-0000000000"}
                """;
        mockMvc.perform(put("/books/" + id).contentType(MediaType.APPLICATION_JSON).content(json))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(id))
                .andExpect(jsonPath("$.title").value("New Title"))
                .andExpect(jsonPath("$.author").value("New Author"))
                .andExpect(jsonPath("$.year").value(2020))
                .andExpect(jsonPath("$.isbn").value("978-0000000000"));
    }

    @Test
    void updateBookNotFoundReturns404() throws Exception {
        mockMvc.perform(put("/books/999999999").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\": \"T\", \"author\": \"A\"}"))
                .andExpect(status().isNotFound());
    }

    @Test
    void updateBookMissingTitleReturns400() throws Exception {
        long id = createBook("Keep Title", "Keep Author", null, null);
        mockMvc.perform(put("/books/" + id).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"author\": \"New Author\"}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void deleteBookReturns204Then404() throws Exception {
        long id = createBook("Doomed Book", "Doomed Author", null, null);
        mockMvc.perform(delete("/books/" + id))
                .andExpect(status().isNoContent());
        mockMvc.perform(get("/books/" + id))
                .andExpect(status().isNotFound());
    }

    @Test
    void deleteBookNotFoundReturns404() throws Exception {
        mockMvc.perform(delete("/books/999999999"))
                .andExpect(status().isNotFound());
    }

    @Test
    void getBookWithNonNumericIdReturns400() throws Exception {
        mockMvc.perform(get("/books/not-a-number"))
                .andExpect(status().isBadRequest());
    }
}
