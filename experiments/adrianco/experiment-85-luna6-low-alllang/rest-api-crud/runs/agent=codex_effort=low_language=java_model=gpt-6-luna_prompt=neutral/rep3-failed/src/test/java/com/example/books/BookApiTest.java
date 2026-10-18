package com.example.books;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;

import static org.hamcrest.Matchers.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest(properties = "spring.datasource.url=jdbc:sqlite:file:books-test?mode=memory&cache=shared")
@AutoConfigureMockMvc
class BookApiTest {
    @Autowired MockMvc mvc;
    @Autowired JdbcTemplate jdbc;

    @org.junit.jupiter.api.BeforeEach
    void clearDatabase() { jdbc.update("DELETE FROM books"); }

    @Test void createsListsFiltersAndReadsBook() throws Exception {
        mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON)
                .content("{\"title\":\"Dune\",\"author\":\"Frank Herbert\",\"year\":1965,\"isbn\":\"123\"}"))
                .andExpect(status().isCreated()).andExpect(jsonPath("$.id").isNumber()).andExpect(jsonPath("$.title").value("Dune"));
        mvc.perform(get("/books?author=Frank%20Herbert")).andExpect(status().isOk()).andExpect(jsonPath("$", hasSize(1)));
        mvc.perform(get("/books/1")).andExpect(status().isOk()).andExpect(jsonPath("$.author").value("Frank Herbert"));
    }

    @Test void updatesAndDeletesBook() throws Exception {
        jdbc.update("INSERT INTO books(title, author) VALUES ('Old', 'Writer')");
        mvc.perform(put("/books/1").contentType(MediaType.APPLICATION_JSON).content("{\"title\":\"New\",\"author\":\"Writer\"}"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.title").value("New"));
        mvc.perform(delete("/books/1")).andExpect(status().isNoContent());
        mvc.perform(get("/books/1")).andExpect(status().isNotFound());
    }

    @Test void validatesRequiredFieldsAndServesHealth() throws Exception {
        mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content("{\"title\":\"  ",\"author\":\"Writer\"}"))
                .andExpect(status().isBadRequest());
        mvc.perform(get("/health")).andExpect(status().isOk()).andExpect(jsonPath("$.status").value("ok"));
    }
}
