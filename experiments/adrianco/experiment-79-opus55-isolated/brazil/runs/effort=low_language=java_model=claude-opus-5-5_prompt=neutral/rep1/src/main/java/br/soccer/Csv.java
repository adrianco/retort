package br.soccer;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Minimal RFC 4180 CSV reader (quoted fields, escaped quotes, embedded newlines, UTF-8 BOM). */
public final class Csv {
    private Csv() {}

    /** Reads a CSV file into rows keyed by header name. Short rows yield missing keys. */
    public static List<Map<String, String>> read(Path file) throws IOException {
        String text = Files.readString(file, StandardCharsets.UTF_8);
        if (text.startsWith("﻿")) text = text.substring(1);
        List<List<String>> rows = parse(text);
        List<Map<String, String>> out = new ArrayList<>();
        if (rows.isEmpty()) return out;
        List<String> header = rows.get(0);
        for (int r = 1; r < rows.size(); r++) {
            List<String> row = rows.get(r);
            if (row.size() == 1 && row.get(0).isBlank()) continue;
            Map<String, String> m = new LinkedHashMap<>();
            for (int c = 0; c < header.size() && c < row.size(); c++) {
                m.put(header.get(c).trim(), row.get(c).trim());
            }
            out.add(m);
        }
        return out;
    }

    static List<List<String>> parse(String text) {
        List<List<String>> rows = new ArrayList<>();
        List<String> row = new ArrayList<>();
        StringBuilder field = new StringBuilder();
        boolean quoted = false;
        int n = text.length();
        for (int i = 0; i < n; i++) {
            char ch = text.charAt(i);
            if (quoted) {
                if (ch == '"') {
                    if (i + 1 < n && text.charAt(i + 1) == '"') {
                        field.append('"');
                        i++;
                    } else {
                        quoted = false;
                    }
                } else {
                    field.append(ch);
                }
            } else if (ch == '"') {
                quoted = true;
            } else if (ch == ',') {
                row.add(field.toString());
                field.setLength(0);
            } else if (ch == '\n' || ch == '\r') {
                if (ch == '\r' && i + 1 < n && text.charAt(i + 1) == '\n') i++;
                row.add(field.toString());
                field.setLength(0);
                rows.add(row);
                row = new ArrayList<>();
            } else {
                field.append(ch);
            }
        }
        if (field.length() > 0 || !row.isEmpty()) {
            row.add(field.toString());
            rows.add(row);
        }
        return rows;
    }
}
