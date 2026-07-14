package com.soccer.mcp.util;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;

public final class DateParser {

    private static final List<DateTimeFormatter> DATE_TIME_FORMATTERS = List.of(
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"),
            DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss")
    );

    private static final List<DateTimeFormatter> DATE_FORMATTERS = List.of(
            DateTimeFormatter.ofPattern("yyyy-MM-dd"),
            DateTimeFormatter.ofPattern("dd/MM/yyyy"),
            DateTimeFormatter.ofPattern("d/M/yyyy")
    );

    private DateParser() {}

    public static LocalDate parse(String s) {
        if (s == null) return null;
        String trimmed = s.trim();
        if (trimmed.isEmpty()) return null;
        for (DateTimeFormatter f : DATE_TIME_FORMATTERS) {
            try {
                return LocalDateTime.parse(trimmed, f).toLocalDate();
            } catch (Exception ignored) { /* try next */ }
        }
        for (DateTimeFormatter f : DATE_FORMATTERS) {
            try {
                return LocalDate.parse(trimmed, f);
            } catch (Exception ignored) { /* try next */ }
        }
        return null;
    }
}
