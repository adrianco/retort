package com.example.brsoccer.csv;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.junit.jupiter.api.Assertions.*;

class DatesTest {

    @Test
    void parsesIsoDate() {
        assertEquals(LocalDate.of(2023, 9, 24), Dates.parse("2023-09-24"));
    }

    @Test
    void parsesIsoDateTimeWithSpace() {
        assertEquals(LocalDate.of(2012, 5, 19), Dates.parse("2012-05-19 18:30:00"));
    }

    @Test
    void parsesBrazilianSlashDate() {
        assertEquals(LocalDate.of(2003, 3, 29), Dates.parse("29/03/2003"));
    }

    @Test
    void returnsNullForBlankOrUnparseable() {
        assertNull(Dates.parse(""));
        assertNull(Dates.parse(null));
        assertNull(Dates.parse("not a date"));
    }
}
