package com.example.books;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class BookControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private BookRepository repository;

    @Autowired
    private ObjectMapper objectMapper;

    @BeforeEach
    void cleanDb() {
        repository.deleteAll();
    }

    @Test
    void healthEndpointReturnsUp() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }

    @Test
    void createBookReturns201AndPersistsIt() throws Exception {
        Book book = new Book("The Hobbit", "Tolkien", 1937, "978-0547928227");

        MvcResult result = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(book)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").exists())
                .andExpect(jsonPath("$.title").value("The Hobbit"))
                .andExpect(jsonPath("$.author").value("Tolkien"))
                .andReturn();

        Book created = objectMapper.readValue(result.getResponse().getContentAsString(), Book.class);

        mockMvc.perform(get("/books/" + created.getId()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("The Hobbit"));
    }

    @Test
    void createWithoutTitleReturns400() throws Exception {
        String body = "{\"author\":\"Someone\",\"year\":2020}";
        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fields.title").exists());
    }

    @Test
    void createWithoutAuthorReturns400() throws Exception {
        String body = "{\"title\":\"Untitled\",\"year\":2020}";
        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fields.author").exists());
    }

    @Test
    void listFilteredByAuthorOnlyReturnsMatchingBooks() throws Exception {
        repository.save(new Book("A", "Alice", 2000, null));
        repository.save(new Book("B", "Bob", 2001, null));
        repository.save(new Book("C", "Alice", 2002, null));

        mockMvc.perform(get("/books").param("author", "Alice"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2))
                .andExpect(jsonPath("$[0].author").value("Alice"))
                .andExpect(jsonPath("$[1].author").value("Alice"));
    }

    @Test
    void updateBookChangesFields() throws Exception {
        Book saved = repository.save(new Book("Old", "Old Author", 1990, "old-isbn"));
        Book payload = new Book("New", "New Author", 2024, "new-isbn");

        mockMvc.perform(put("/books/" + saved.getId())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(payload)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("New"))
                .andExpect(jsonPath("$.author").value("New Author"))
                .andExpect(jsonPath("$.year").value(2024))
                .andExpect(jsonPath("$.isbn").value("new-isbn"));
    }

    @Test
    void deleteBookReturns204AndRemovesIt() throws Exception {
        Book saved = repository.save(new Book("Doomed", "Author", 2000, null));

        mockMvc.perform(delete("/books/" + saved.getId()))
                .andExpect(status().isNoContent());

        mockMvc.perform(get("/books/" + saved.getId()))
                .andExpect(status().isNotFound());
    }

    @Test
    void getNonExistentBookReturns404() throws Exception {
        mockMvc.perform(get("/books/999999"))
                .andExpect(status().isNotFound());
    }
}
