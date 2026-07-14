/*
 * ============================================================================
 * Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 * File:    Dates.java
 * Purpose: Tolerant date parsing for the heterogeneous match files, which mix
 *          ISO dates ("2023-09-24"), ISO date-times ("2012-05-19 18:30:00")
 *          and Brazilian day/month/year dates ("29/03/2003"). Always returns a
 *          LocalDate (time component discarded) or null when unparseable.
 * Part of: csv package (field-level parsing helpers).
 * ============================================================================
 */
package com.example.brsoccer.csv;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;

/** Parses the several date formats present across the datasets. */
public final class Dates {

    private static final DateTimeFormatter BR_SLASH = DateTimeFormatter.ofPattern("dd/MM/yyyy");

    private Dates() {
    }

    /** Parse a date string into a {@link LocalDate}, or null if blank/unrecognized. */
    public static LocalDate parse(String raw) {
        if (raw == null) {
            return null;
        }
        String s = raw.trim();
        if (s.isEmpty()) {
            return null;
        }
        // Drop any time component separated by a space (e.g. "2012-05-19 18:30:00").
        int space = s.indexOf(' ');
        String datePart = space > 0 ? s.substring(0, space) : s;
        try {
            if (datePart.contains("/")) {
                return LocalDate.parse(datePart, BR_SLASH);
            }
            return LocalDate.parse(datePart);
        } catch (RuntimeException e) {
            return null;
        }
    }
}
