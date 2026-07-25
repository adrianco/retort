package com.example.bookapi.web.dto;

import com.fasterxml.jackson.annotation.JsonInclude;

import java.time.Instant;
import java.util.List;

/** Uniform JSON error body returned for every non-2xx response. */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record ApiError(
        Instant timestamp,
        int status,
        String error,
        String message,
        List<FieldError> fieldErrors) {

    public record FieldError(String field, String message) {
    }
}
