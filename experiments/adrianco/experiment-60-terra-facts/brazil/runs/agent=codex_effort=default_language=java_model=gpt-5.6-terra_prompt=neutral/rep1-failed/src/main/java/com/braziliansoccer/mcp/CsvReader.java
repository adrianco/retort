package com.braziliansoccer.mcp;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.*;

/** Small RFC-4180 capable reader; keeps the server dependency-free. */
final class CsvReader {
    private CsvReader() {}
    static List<Map<String, String>> read(Path path) throws IOException {
        try (Reader source = new BufferedReader(new InputStreamReader(new FileInputStream(path.toFile()), StandardCharsets.UTF_8))) {
            List<List<String>> rows = parse(source);
            if (rows.isEmpty()) return List.of();
            List<String> headers = rows.getFirst();
            if (!headers.isEmpty()) headers.set(0, headers.getFirst().replace("\uFEFF", ""));
            List<Map<String, String>> output = new ArrayList<>();
            for (int r = 1; r < rows.size(); r++) {
                Map<String, String> row = new LinkedHashMap<>();
                for (int c = 0; c < headers.size(); c++) row.put(headers.get(c), c < rows.get(r).size() ? rows.get(r).get(c).trim() : "");
                output.add(row);
            }
            return output;
        }
    }
    private static List<List<String>> parse(Reader input) throws IOException {
        List<List<String>> result = new ArrayList<>(); List<String> row = new ArrayList<>(); StringBuilder field = new StringBuilder();
        boolean quoted = false; int ch;
        while ((ch = input.read()) != -1) { char c = (char) ch;
            if (c == '"') { if (quoted && input.markSupported()) { input.mark(1); int next = input.read(); if (next == '"') field.append('"'); else { quoted = false; if (next != -1) input.reset(); } } else quoted = !quoted; }
            else if (c == ',' && !quoted) { row.add(field.toString()); field.setLength(0); }
            else if ((c == '\n' || c == '\r') && !quoted) { if (c == '\r') { input.mark(1); if (input.read() != '\n') input.reset(); } row.add(field.toString()); field.setLength(0); result.add(row); row = new ArrayList<>(); }
            else field.append(c);
        }
        if (!row.isEmpty() || !field.isEmpty()) { row.add(field.toString()); result.add(row); }
        return result;
    }
}
