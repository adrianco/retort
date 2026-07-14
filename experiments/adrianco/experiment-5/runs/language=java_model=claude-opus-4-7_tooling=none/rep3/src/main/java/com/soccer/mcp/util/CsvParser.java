package com.soccer.mcp.util;

import java.io.IOException;
import java.io.PushbackReader;
import java.io.Reader;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Consumer;

public final class CsvParser {

    private CsvParser() {}

    public static void parse(Reader reader, Consumer<List<String>> rowConsumer) throws IOException {
        PushbackReader pr = new PushbackReader(reader, 2);
        List<String> row = new ArrayList<>();
        StringBuilder field = new StringBuilder();
        boolean inQuote = false;
        boolean fieldStarted = false;
        int c;
        while ((c = pr.read()) != -1) {
            char ch = (char) c;
            if (inQuote) {
                if (ch == '"') {
                    int next = pr.read();
                    if (next == '"') {
                        field.append('"');
                    } else {
                        inQuote = false;
                        if (next != -1) pr.unread(next);
                    }
                } else {
                    field.append(ch);
                }
            } else {
                if (ch == '"' && !fieldStarted) {
                    inQuote = true;
                    fieldStarted = true;
                } else if (ch == ',') {
                    row.add(field.toString());
                    field.setLength(0);
                    fieldStarted = false;
                } else if (ch == '\n') {
                    row.add(field.toString());
                    field.setLength(0);
                    fieldStarted = false;
                    rowConsumer.accept(row);
                    row = new ArrayList<>();
                } else if (ch == '\r') {
                    // ignore
                } else {
                    field.append(ch);
                    fieldStarted = true;
                }
            }
        }
        if (fieldStarted || !row.isEmpty()) {
            row.add(field.toString());
            rowConsumer.accept(row);
        }
    }

    public static List<List<String>> parseAll(Reader reader) throws IOException {
        List<List<String>> rows = new ArrayList<>();
        parse(reader, rows::add);
        return rows;
    }
}
