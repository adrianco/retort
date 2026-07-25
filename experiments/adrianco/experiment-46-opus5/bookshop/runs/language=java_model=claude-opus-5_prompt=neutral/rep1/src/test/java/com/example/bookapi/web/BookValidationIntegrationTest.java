package com.example.bookapi.web;

import com.example.bookapi.AbstractIntegrationTest;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class BookValidationIntegrationTest extends AbstractIntegrationTest {

    @Test
    @DisplayName("A missing title and author produce 400 listing both fields")
    void missingRequiredFieldsAreRejected() throws Exception {
        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"year\": 1965}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.status").value(400))
                .andExpect(jsonPath("$.message").value("Validation failed"))
                .andExpect(jsonPath("$.fieldErrors", hasSize(2)))
                .andExpect(jsonPath("$.fieldErrors[0].field").value("author"))
                .andExpect(jsonPath("$.fieldErrors[0].message").value("author is required"))
                .andExpect(jsonPath("$.fieldErrors[1].field").value("title"))
                .andExpect(jsonPath("$.fieldErrors[1].message").value("title is required"));

        mockMvc.perform(get("/books")).andExpect(jsonPath("$", hasSize(0)));
    }

    @Test
    @DisplayName("A whitespace-only title is not a title")
    void blankTitleIsRejected() throws Exception {
        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\": \"   \", \"author\": \"Frank Herbert\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fieldErrors[0].field").value("title"));
    }

    @Test
    @DisplayName("PUT is validated the same way as POST")
    void updateIsValidated() throws Exception {
        String created = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\": \"Dune\", \"author\": \"Frank Herbert\"}"))
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString();
        long id = objectMapper.readTree(created).get("id").asLong();

        mockMvc.perform(put("/books/{id}", id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\": \"Dune\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fieldErrors[0].field").value("author"));

        mockMvc.perform(get("/books/{id}", id)).andExpect(jsonPath("$.title").value("Dune"));
    }

    @Test
    @DisplayName("An out-of-range year is rejected")
    void implausibleYearIsRejected() throws Exception {
        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\": \"Dune\", \"author\": \"Frank Herbert\", \"year\": 99999}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fieldErrors[0].field").value("year"));
    }

    @Test
    @DisplayName("A malformed ISBN is rejected, a hyphenated one is normalised")
    void isbnIsValidatedAndNormalised() throws Exception {
        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\": \"Dune\", \"author\": \"Frank Herbert\", \"isbn\": \"not-an-isbn\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fieldErrors[0].field").value("isbn"));

        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\": \"Dune\", \"author\": \"Frank Herbert\", "
                                + "\"isbn\": \"978-0-441-01359-3\"}"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.isbn").value("9780441013593"));
    }

    @Test
    @DisplayName("Reusing an ISBN returns 409")
    void duplicateIsbnIsRejected() throws Exception {
        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\": \"Dune\", \"author\": \"Frank Herbert\", \"isbn\": \"0441172717\"}"))
                .andExpect(status().isCreated());

        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\": \"Dune reprint\", \"author\": \"Frank Herbert\", "
                                + "\"isbn\": \"0-441-17271-7\"}"))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.status").value(409));

        mockMvc.perform(get("/books")).andExpect(jsonPath("$", hasSize(1)));
    }

    @Test
    @DisplayName("Re-saving a book with its own ISBN is not a conflict")
    void updateKeepingOwnIsbnIsAllowed() throws Exception {
        String created = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\": \"Dune\", \"author\": \"Frank Herbert\", \"isbn\": \"0441172717\"}"))
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString();
        long id = objectMapper.readTree(created).get("id").asLong();

        mockMvc.perform(put("/books/{id}", id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\": \"Dune\", \"author\": \"F. Herbert\", \"isbn\": \"0441172717\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.author").value("F. Herbert"));
    }

    @Test
    @DisplayName("Malformed JSON produces 400, not 500")
    void malformedJsonIsRejected() throws Exception {
        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\": \"Dune\", "))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("Malformed JSON request body"));
    }

    @Test
    @DisplayName("An unknown path returns a JSON 404")
    void unknownPathReturnsJsonError() throws Exception {
        mockMvc.perform(get("/nope"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.status").value(404));
    }

    @Test
    @DisplayName("A non-JSON body is refused with 415")
    void wrongContentTypeIsRejected() throws Exception {
        mockMvc.perform(post("/books")
                        .contentType(MediaType.TEXT_PLAIN)
                        .content("title=Dune"))
                .andExpect(status().isUnsupportedMediaType())
                .andExpect(jsonPath("$.status").value(415));
    }

    @Test
    @DisplayName("The wrong method on a valid path gives 405")
    void wrongMethodIsRejected() throws Exception {
        mockMvc.perform(delete("/books"))
                .andExpect(status().isMethodNotAllowed())
                .andExpect(jsonPath("$.status").value(405));
    }
}
