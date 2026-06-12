/*
 * ============================================================================
 *  Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 *  File    : CsvReader.java
 *  Purpose : A small, dependency-free RFC-4180 style CSV parser.
 *
 *  Context : The Kaggle datasets in data/kaggle/ use a mixture of quoted and
 *            unquoted fields, embedded commas inside quotes, a UTF-8 BOM on at
 *            least one file (fifa_data.csv) and Brazilian-Portuguese accented
 *            characters. This reader handles all of that without pulling in a
 *            third-party CSV dependency, returning each row as a list of
 *            already-unquoted string fields. Files are always read as UTF-8.
 *
 *  Used by : com.brasileirao.mcp.data.KnowledgeGraph
 * ============================================================================
 */
package com.brasileirao.mcp.util;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Consumer;

/** Streaming CSV parser that yields one {@code List<String>} per record. */
public final class CsvReader {

    private CsvReader() {
    }

    /** Parse a file on disk, invoking {@code rowConsumer} for every record (header included). */
    public static void parse(Path path, Consumer<List<String>> rowConsumer) throws IOException {
        try (InputStream in = Files.newInputStream(path)) {
            parse(in, rowConsumer);
        }
    }

    /** Parse a stream, invoking {@code rowConsumer} for every record (header included). */
    public static void parse(InputStream in, Consumer<List<String>> rowConsumer) throws IOException {
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))) {
            StringBuilder field = new StringBuilder();
            List<String> row = new ArrayList<>();
            boolean inQuotes = false;
            boolean firstCharOfRow = true;
            boolean rowHasContent = false;

            int c;
            while ((c = reader.read()) != -1) {
                char ch = (char) c;

                // Strip a UTF-8 BOM if it appears as the very first character.
                if (firstCharOfRow && row.isEmpty() && field.length() == 0 && ch == '﻿') {
                    continue;
                }
                firstCharOfRow = false;

                if (inQuotes) {
                    if (ch == '"') {
                        // A doubled quote ("") is an escaped quote inside the field.
                        int next = reader.read();
                        if (next == '"') {
                            field.append('"');
                        } else {
                            inQuotes = false;
                            // Re-process the lookahead character.
                            if (next == -1) {
                                break;
                            }
                            ch = (char) next;
                            if (ch == ',') {
                                row.add(field.toString());
                                field.setLength(0);
                                rowHasContent = true;
                            } else if (ch == '\n' || ch == '\r') {
                                handleLineEnd(ch, reader, row, field, rowConsumer);
                                row = new ArrayList<>();
                                field.setLength(0);
                                rowHasContent = false;
                            } else {
                                field.append(ch);
                            }
                        }
                    } else {
                        field.append(ch);
                    }
                    continue;
                }

                if (ch == '"') {
                    inQuotes = true;
                } else if (ch == ',') {
                    row.add(field.toString());
                    field.setLength(0);
                    rowHasContent = true;
                } else if (ch == '\n' || ch == '\r') {
                    if (rowHasContent || field.length() > 0) {
                        handleLineEnd(ch, reader, row, field, rowConsumer);
                        row = new ArrayList<>();
                        field.setLength(0);
                        rowHasContent = false;
                    } else if (ch == '\r') {
                        // Swallow the paired \n of a blank \r\n line.
                        reader.mark(1);
                        int next = reader.read();
                        if (next != '\n' && next != -1) {
                            reader.reset();
                        }
                    }
                } else {
                    field.append(ch);
                }
            }

            // Flush a trailing record with no final newline.
            if (field.length() > 0 || rowHasContent) {
                row.add(field.toString());
                rowConsumer.accept(row);
            }
        }
    }

    private static void handleLineEnd(char ch, BufferedReader reader, List<String> row,
                                      StringBuilder field, Consumer<List<String>> rowConsumer) throws IOException {
        row.add(field.toString());
        if (ch == '\r') {
            reader.mark(1);
            int next = reader.read();
            if (next != '\n' && next != -1) {
                reader.reset();
            }
        }
        rowConsumer.accept(row);
    }
}
