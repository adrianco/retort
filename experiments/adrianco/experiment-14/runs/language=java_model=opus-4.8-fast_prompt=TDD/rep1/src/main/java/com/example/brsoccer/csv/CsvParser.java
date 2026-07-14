/*
 * ============================================================================
 * Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 * File:    CsvParser.java
 * Purpose: Minimal, dependency-free RFC-4180-style CSV reader used to load the
 *          Kaggle datasets. Handles quoted fields, embedded commas/newlines,
 *          escaped double-quotes, a leading UTF-8 byte-order mark and blank
 *          lines. All input is treated as UTF-8 text by callers.
 * Part of: csv package (raw text -> rows of string fields).
 * ============================================================================
 */
package com.example.brsoccer.csv;

import java.io.IOException;
import java.io.Reader;
import java.io.UncheckedIOException;
import java.util.ArrayList;
import java.util.List;

/** Parses CSV text into a list of rows, where each row is a list of fields. */
public final class CsvParser {

    private static final char BOM = '﻿';

    private CsvParser() {
    }

    /** Parse all rows from the given reader. Blank lines (zero non-empty fields) are skipped. */
    public static List<List<String>> parse(Reader reader) {
        String content = readAll(reader);
        List<List<String>> rows = new ArrayList<>();
        List<String> row = new ArrayList<>();
        StringBuilder field = new StringBuilder();
        boolean inQuotes = false;
        boolean rowHasContent = false;

        int i = 0;
        int n = content.length();
        if (n > 0 && content.charAt(0) == BOM) {
            i = 1;
        }

        for (; i < n; i++) {
            char c = content.charAt(i);
            if (inQuotes) {
                if (c == '"') {
                    if (i + 1 < n && content.charAt(i + 1) == '"') {
                        field.append('"');
                        i++;
                    } else {
                        inQuotes = false;
                    }
                } else {
                    field.append(c);
                }
                continue;
            }
            switch (c) {
                case '"' -> {
                    inQuotes = true;
                    rowHasContent = true;
                }
                case ',' -> {
                    row.add(field.toString());
                    field.setLength(0);
                    rowHasContent = true;
                }
                case '\r' -> {
                    // ignore; the following \n (or end of input) terminates the row
                }
                case '\n' -> {
                    row.add(field.toString());
                    field.setLength(0);
                    if (rowHasContent) {
                        rows.add(row);
                    }
                    row = new ArrayList<>();
                    rowHasContent = false;
                }
                default -> {
                    field.append(c);
                    rowHasContent = true;
                }
            }
        }
        // flush trailing field/row when input does not end in a newline
        if (rowHasContent || field.length() > 0) {
            row.add(field.toString());
            if (rowHasContent) {
                rows.add(row);
            }
        }
        return rows;
    }

    private static String readAll(Reader reader) {
        StringBuilder sb = new StringBuilder();
        char[] buf = new char[8192];
        int read;
        try (Reader r = reader) {
            while ((read = r.read(buf)) != -1) {
                sb.append(buf, 0, read);
            }
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        return sb.toString();
    }
}
