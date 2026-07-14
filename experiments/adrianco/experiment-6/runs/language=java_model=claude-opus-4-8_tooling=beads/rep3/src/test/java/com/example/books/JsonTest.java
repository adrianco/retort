package com.example.books;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;

class JsonTest {

    @Test
    @SuppressWarnings("unchecked")
    void parsesObjectWithMixedTypes() {
        Map<String, Object> obj = (Map<String, Object>) Json.parse(
            "{\"title\":\"Dune\",\"year\":1965,\"sequel\":true,\"isbn\":null}");
        assertEquals("Dune", obj.get("title"));
        assertEquals(1965.0, ((Number) obj.get("year")).doubleValue());
        assertEquals(Boolean.TRUE, obj.get("sequel"));
        assertTrue(obj.containsKey("isbn"));
        assertNull(obj.get("isbn"));
    }

    @Test
    @SuppressWarnings("unchecked")
    void parsesArrays() {
        List<Object> arr = (List<Object>) Json.parse("[1, \"two\", false]");
        assertEquals(3, arr.size());
        assertEquals("two", arr.get(1));
    }

    @Test
    void handlesEscapesInStrings() {
        Map<String, Object> obj = Json.parseObject("{\"q\":\"a\\\"b\\nc\"}");
        assertEquals("a\"b\nc", obj.get("q"));
    }

    @Test
    void roundTripsThroughWrite() {
        String json = "{\"id\":1,\"title\":\"Dune\",\"year\":1965}";
        Object parsed = Json.parse(json);
        String written = Json.write(parsed);
        // Re-parse to compare structurally (whitespace/format independent).
        assertEquals(parsed, Json.parse(written));
    }

    @Test
    void writesIntegralNumbersWithoutDecimalPoint() {
        assertEquals("{\"year\":1965}", Json.write(Map.of("year", 1965)));
    }

    @Test
    void escapesSpecialCharactersOnWrite() {
        assertEquals("\"a\\\"b\"", Json.write("a\"b"));
    }

    @Test
    void rejectsInvalidJson() {
        assertThrows(Json.JsonException.class, () -> Json.parse("{not json"));
        assertThrows(Json.JsonException.class, () -> Json.parse(""));
        assertThrows(Json.JsonException.class, () -> Json.parse("[1, 2"));
        assertThrows(Json.JsonException.class, () -> Json.parseObject("[1, 2, 3]"));
    }
}
