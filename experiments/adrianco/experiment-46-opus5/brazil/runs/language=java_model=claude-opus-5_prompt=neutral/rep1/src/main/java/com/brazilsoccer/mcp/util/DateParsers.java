package com.brazilsoccer.mcp.util;

import java.time.LocalDate;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.Optional;

/**
 * Tolerant date/time parsing for the several formats found in the datasets:
 * ISO ({@code 2023-09-24}), ISO with time ({@code 2012-05-19 18:30:00}), Brazilian
 * ({@code 29/03/2003}) and the literal placeholders {@code NA} / {@code -} used for
 * matches with unknown dates.
 */
public final class DateParsers {

    private static final DateTimeFormatter BR_DATE = DateTimeFormatter.ofPattern("dd/MM/uuuu");

    private DateParsers() {
    }

    /** Parses the date part of any supported format. */
    public static Optional<LocalDate> parseDate(String raw) {
        String value = clean(raw);
        if (value == null) {
            return Optional.empty();
        }
        String datePart = value.contains(" ") ? value.substring(0, value.indexOf(' ')) : value;
        if (datePart.contains("/")) {
            try {
                return Optional.of(LocalDate.parse(datePart, BR_DATE));
            } catch (DateTimeParseException e) {
                return Optional.empty();
            }
        }
        try {
            return Optional.of(LocalDate.parse(datePart));
        } catch (DateTimeParseException e) {
            return Optional.empty();
        }
    }

    /** Parses a kick-off time, either from a datetime string or from a standalone time column. */
    public static Optional<LocalTime> parseTime(String raw) {
        String value = clean(raw);
        if (value == null) {
            return Optional.empty();
        }
        String timePart = value.contains(" ") ? value.substring(value.indexOf(' ') + 1) : value;
        if (!timePart.contains(":")) {
            return Optional.empty();
        }
        try {
            return Optional.of(LocalTime.parse(timePart.length() == 5 ? timePart + ":00" : timePart));
        } catch (DateTimeParseException e) {
            return Optional.empty();
        }
    }

    /** Parses an integer, returning empty for {@code NA}, {@code -}, decimals such as {@code 2.0}. */
    public static Optional<Integer> parseInt(String raw) {
        String value = clean(raw);
        if (value == null) {
            return Optional.empty();
        }
        if (value.endsWith(".0")) {
            value = value.substring(0, value.length() - 2);
        }
        try {
            return Optional.of(Integer.parseInt(value));
        } catch (NumberFormatException e) {
            try {
                return Optional.of((int) Math.round(Double.parseDouble(value)));
            } catch (NumberFormatException ignored) {
                return Optional.empty();
            }
        }
    }

    private static String clean(String raw) {
        if (raw == null) {
            return null;
        }
        String value = raw.trim().replace("\"", "");
        if (value.isEmpty() || value.equalsIgnoreCase("NA") || value.equals("-") || value.equalsIgnoreCase("null")) {
            return null;
        }
        return value;
    }
}
