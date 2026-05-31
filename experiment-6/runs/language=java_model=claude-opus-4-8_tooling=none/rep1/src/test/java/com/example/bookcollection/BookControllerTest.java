package com.example.bookcollection;

import static org.hamcrest.Matchers.is;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import com.fasterxml.jackson.databind.ObjectMapper;

@SpringBootTest
@AutoConfigureMockMvc
class BookControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private BookRepository repository;

    @BeforeEach
    void clean() {
        repository.deleteAll();
    }

    private String json(String title, String author, Integer year, String isbn) throws Exception {
        BookRequest request = new BookRequest();
        request.setTitle(title);
        request.setAuthor(author);
        request.setYear(year);
        request.setIsbn(isbn);
        return objectMapper.writeValueAsString(request);
    }

    @Test
    void createBookReturns201AndPersists() throws Exception {
        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json("Dune", "Frank Herbert", 1965, "978-0441013593")))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id", is(notNullNumber())))
                .andExpect(jsonPath("$.title", is("Dune")))
                .andExpect(jsonPath("$.author", is("Frank Herbert")));
    }

    @Test
    void createBookWithoutTitleReturns400() throws Exception {
        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(null, "Frank Herbert", 1965, "isbn")))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.title", is("title is required")));
    }

    @Test
    void listBooksFiltersByAuthor() throws Exception {
        mockMvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON)
                .content(json("Dune", "Frank Herbert", 1965, "a")));
        mockMvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON)
                .content(json("Neuromancer", "William Gibson", 1984, "b")));

        mockMvc.perform(get("/books").param("author", "Frank Herbert"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()", is(1)))
                .andExpect(jsonPath("$[0].title", is("Dune")));

        mockMvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()", is(2)));
    }

    @Test
    void getUpdateAndDeleteLifecycle() throws Exception {
        String location = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json("Dune", "Frank Herbert", 1965, "a")))
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString();
        Long id = objectMapper.readTree(location).get("id").asLong();

        mockMvc.perform(get("/books/{id}", id))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title", is("Dune")));

        mockMvc.perform(put("/books/{id}", id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json("Dune Messiah", "Frank Herbert", 1969, "a")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title", is("Dune Messiah")))
                .andExpect(jsonPath("$.year", is(1969)));

        mockMvc.perform(delete("/books/{id}", id))
                .andExpect(status().isNoContent());

        mockMvc.perform(get("/books/{id}", id))
                .andExpect(status().isNotFound());
    }

    @Test
    void getMissingBookReturns404() throws Exception {
        mockMvc.perform(get("/books/{id}", 99999))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.status", is(404)));
    }

    @Test
    void healthEndpointReturnsUp() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status", is("UP")));
    }

    private static org.hamcrest.Matcher<Object> notNullNumber() {
        return org.hamcrest.Matchers.notNullValue();
    }
}
