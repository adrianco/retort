package com.example.books;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.Map;

/**
 * Small JSON helpers built on Jackson.
 */
public final class Json {

    public static final ObjectMapper MAPPER = new ObjectMapper();

    private Json() {
    }

    public static byte[] write(Object value) {
        try {
            return MAPPER.writeValueAsBytes(value);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("Failed to serialize " + value.getClass().getSimpleName(), e);
        }
    }

    /**
     * Parses a request body into a {@link BookInput}.
     * Throws a 400 {@link BookException} when the body is missing or not valid JSON.
     */
    public static BookInput readBookInput(byte[] body) {
        if (body == null || body.length == 0) {
            throw new BookException(400, "Request body is required");
        }
        try {
            return MAPPER.readValue(body, BookInput.class);
        } catch (com.fasterxml.jackson.core.JsonProcessingException e) {
            throw new BookException(400, "Request body must be valid JSON");
        } catch (java.io.IOException e) {
            throw new BookException(400, "Request body must be valid JSON");
        }
    }

    public static byte[] error(String message) {
        return write(Map.of("error", message));
    }
}
