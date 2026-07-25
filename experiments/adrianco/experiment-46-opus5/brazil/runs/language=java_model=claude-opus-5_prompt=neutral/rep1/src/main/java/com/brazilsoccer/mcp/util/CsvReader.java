package com.brazilsoccer.mcp.util;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Consumer;

/**
 * Minimal RFC-4180 CSV reader used by the data loaders.
 *
 * <p>The bundled Kaggle files mix conventions: quoted and unquoted fields, embedded commas
 * ("Jul 1, 2004"), a UTF-8 BOM on {@code fifa_data.csv} and Portuguese accents everywhere. A tiny
 * hand written parser keeps the project dependency free while handling all of that; files are
 * streamed row by row so the 9 MB player file never has to be materialised as text.
 */
public final class CsvReader {

    private CsvReader() {
    }

    /** One CSV record with by-name access to its columns. */
    public static final class Row {
        private final Map<String, Integer> header;
        private final List<String> values;
        private final long lineNumber;

        Row(Map<String, Integer> header, List<String> values, long lineNumber) {
            this.header = header;
            this.values = values;
            this.lineNumber = lineNumber;
        }

        /** Trimmed column value, or {@code null} when the column is missing or empty. */
        public String get(String column) {
            Integer index = header.get(column);
            if (index == null || index >= values.size()) {
                return null;
            }
            String value = values.get(index).trim();
            return value.isEmpty() ? null : value;
        }

        public String getOrDefault(String column, String fallback) {
            String value = get(column);
            return value == null ? fallback : value;
        }

        public long lineNumber() {
            return lineNumber;
        }

        public List<String> values() {
            return List.copyOf(values);
        }
    }

    /** Reads a UTF-8 CSV file and hands every data row to {@code consumer}. */
    public static void forEachRow(Path file, Consumer<Row> consumer) {
        try (BufferedReader reader = Files.newBufferedReader(file, StandardCharsets.UTF_8)) {
            parse(reader, consumer);
        } catch (IOException e) {
            throw new UncheckedIOException("Failed to read CSV file: " + file, e);
        }
    }

    public static List<Row> readAll(Path file) {
        List<Row> rows = new ArrayList<>();
        forEachRow(file, rows::add);
        return rows;
    }

    static void parse(Reader reader, Consumer<Row> consumer) throws IOException {
        Map<String, Integer> header = null;
        long lineNumber = 0;
        List<String> record;
        boolean first = true;
        while ((record = readRecord(reader, first)) != null) {
            first = false;
            lineNumber++;
            if (header == null) {
                header = new HashMap<>();
                for (int i = 0; i < record.size(); i++) {
                    header.put(record.get(i).trim(), i);
                }
                continue;
            }
            if (record.size() == 1 && record.get(0).isBlank()) {
                continue; // trailing blank line
            }
            consumer.accept(new Row(header, record, lineNumber));
        }
    }

    /** Reads one logical CSV record (which may span several physical lines inside quotes). */
    private static List<String> readRecord(Reader reader, boolean stripBom) throws IOException {
        List<String> fields = new ArrayList<>();
        StringBuilder field = new StringBuilder();
        boolean inQuotes = false;
        boolean sawAnything = false;
        int c;
        while ((c = reader.read()) != -1) {
            sawAnything = true;
            char ch = (char) c;
            if (stripBom && fields.isEmpty() && field.isEmpty() && ch == '﻿') {
                continue;
            }
            if (inQuotes) {
                if (ch == '"') {
                    int next = reader.read();
                    if (next == '"') {
                        field.append('"');
                    } else {
                        inQuotes = false;
                        if (next == -1) {
                            break;
                        }
                        // Re-handle the character that ended the quoted section.
                        if (next == ',') {
                            fields.add(field.toString());
                            field.setLength(0);
                        } else if (next == '\n') {
                            fields.add(field.toString());
                            return fields;
                        } else if (next != '\r') {
                            field.append((char) next);
                        }
                    }
                } else {
                    field.append(ch);
                }
            } else if (ch == '"' && field.isEmpty()) {
                inQuotes = true;
            } else if (ch == ',') {
                fields.add(field.toString());
                field.setLength(0);
            } else if (ch == '\n') {
                fields.add(field.toString());
                return fields;
            } else if (ch != '\r') {
                field.append(ch);
            }
        }
        if (!sawAnything) {
            return null;
        }
        fields.add(field.toString());
        return fields;
    }
}
