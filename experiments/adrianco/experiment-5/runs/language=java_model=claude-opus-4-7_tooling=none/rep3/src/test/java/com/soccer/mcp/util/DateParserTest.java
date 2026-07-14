package com.soccer.mcp.util;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

class DateParserTest {

    @Test
    void givenIsoDate_whenParsed_thenReturnsLocalDate() {
        assertEquals(LocalDate.of(2023, 9, 24), DateParser.parse("2023-09-24"));
    }

    @Test
    void givenIsoDateTime_whenParsed_thenReturnsDatePart() {
        assertEquals(LocalDate.of(2012, 5, 19), DateParser.parse("2012-05-19 18:30:00"));
    }

    @Test
    void givenBrazilianDate_whenParsed_thenReturnsLocalDate() {
        assertEquals(LocalDate.of(2003, 3, 29), DateParser.parse("29/03/2003"));
    }

    @Test
    void givenEmptyString_whenParsed_thenNull() {
        assertNull(DateParser.parse(""));
        assertNull(DateParser.parse(null));
    }
}
