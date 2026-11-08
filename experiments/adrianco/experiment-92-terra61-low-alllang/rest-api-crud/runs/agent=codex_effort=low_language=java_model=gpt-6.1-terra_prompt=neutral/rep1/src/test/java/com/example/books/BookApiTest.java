package com.example.books;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import com.fasterxml.jackson.databind.ObjectMapper;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest(properties = "spring.datasource.url=jdbc:sqlite:file:books-test?mode=memory&cache=shared")
@AutoConfigureMockMvc
class BookApiTest {
    @Autowired MockMvc mvc;
    @Autowired JdbcTemplate db;
    @Autowired ObjectMapper json;

    @BeforeEach void clean() { db.update("DELETE FROM books"); }

    private long create(String body) throws Exception {
        MvcResult result = mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isCreated()).andExpect(header().exists("Location")).andReturn();
        return json.readTree(result.getResponse().getContentAsString()).get("id").asLong();
    }

    @Test void createGetAndFilter() throws Exception {
        long id = create("{\"title\":\"Dune\",\"author\":\"Herbert\",\"year\":1965,\"isbn\":\"0123\"}");
        create("{\"title\":\"Other\",\"author\":\"Someone\"}");
        mvc.perform(get("/books/" + id)).andExpect(status().isOk()).andExpect(jsonPath("$.isbn").value("0123"));
        mvc.perform(get("/books").param("author", "Herbert")).andExpect(status().isOk()).andExpect(jsonPath("$.length()").value(1)).andExpect(jsonPath("$[0].title").value("Dune"));
        mvc.perform(get("/books")).andExpect(jsonPath("$.length()").value(2));
    }

    @Test void updateAndDelete() throws Exception {
        long id = create("{\"title\":\"Old\",\"author\":\"A\"}");
        mvc.perform(put("/books/" + id).contentType(MediaType.APPLICATION_JSON).content("{\"title\":\"New\",\"author\":\"B\",\"year\":2000}"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.title").value("New")).andExpect(jsonPath("$.year").value(2000));
        mvc.perform(delete("/books/" + id)).andExpect(status().isNoContent());
        mvc.perform(get("/books/" + id)).andExpect(status().isNotFound());
        mvc.perform(delete("/books/" + id)).andExpect(status().isNotFound());
        mvc.perform(put("/books/" + id).contentType(MediaType.APPLICATION_JSON).content("{\"title\":\"X\",\"author\":\"Y\"}")).andExpect(status().isNotFound());
    }

    @Test void validatesInputsAndHealth() throws Exception {
        mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content("{\"title\":\"  \",\"author\":\"A\"}")).andExpect(status().isBadRequest());
        mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content("{\"title\":\"X\"}")).andExpect(status().isBadRequest());
        mvc.perform(put("/books/1").contentType(MediaType.APPLICATION_JSON).content("{\"title\":\"X\"}")).andExpect(status().isBadRequest());
        mvc.perform(get("/health")).andExpect(status().isOk()).andExpect(jsonPath("$.status").value("ok"));
    }
}
