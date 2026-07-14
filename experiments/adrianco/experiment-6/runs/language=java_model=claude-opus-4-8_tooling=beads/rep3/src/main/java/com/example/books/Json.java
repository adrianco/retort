package com.example.books;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * A small, dependency-free JSON parser and writer.
 *
 * <p>Supports the subset of JSON the API needs: objects, arrays, strings,
 * numbers, booleans and null. {@link #parse(String)} returns {@link Map},
 * {@link List}, {@link String}, {@link Double}, {@link Boolean} or {@code null}.
 */
public final class Json {

    /** Thrown when input is not valid JSON. */
    public static final class JsonException extends RuntimeException {
        public JsonException(String message) {
            super(message);
        }
    }

    private Json() {
    }

    // ----- Parsing -------------------------------------------------------

    public static Object parse(String text) {
        Parser p = new Parser(text);
        p.skipWs();
        Object value = p.parseValue();
        p.skipWs();
        if (!p.atEnd()) {
            throw new JsonException("unexpected trailing content at position " + p.pos);
        }
        return value;
    }

    /** Parses {@code text} and requires it to be a JSON object. */
    @SuppressWarnings("unchecked")
    public static Map<String, Object> parseObject(String text) {
        Object value = parse(text);
        if (!(value instanceof Map)) {
            throw new JsonException("expected a JSON object");
        }
        return (Map<String, Object>) value;
    }

    private static final class Parser {
        private final String s;
        private int pos;

        Parser(String s) {
            this.s = s;
        }

        boolean atEnd() {
            return pos >= s.length();
        }

        void skipWs() {
            while (pos < s.length() && Character.isWhitespace(s.charAt(pos))) {
                pos++;
            }
        }

        Object parseValue() {
            if (atEnd()) {
                throw new JsonException("unexpected end of input");
            }
            char c = s.charAt(pos);
            switch (c) {
                case '{':
                    return parseObjectBody();
                case '[':
                    return parseArrayBody();
                case '"':
                    return parseString();
                case 't':
                case 'f':
                    return parseBoolean();
                case 'n':
                    return parseNull();
                default:
                    return parseNumber();
            }
        }

        private Map<String, Object> parseObjectBody() {
            Map<String, Object> map = new LinkedHashMap<>();
            expect('{');
            skipWs();
            if (peek() == '}') {
                pos++;
                return map;
            }
            while (true) {
                skipWs();
                if (peek() != '"') {
                    throw new JsonException("expected string key at position " + pos);
                }
                String key = parseString();
                skipWs();
                expect(':');
                skipWs();
                map.put(key, parseValue());
                skipWs();
                char c = next();
                if (c == '}') {
                    break;
                }
                if (c != ',') {
                    throw new JsonException("expected ',' or '}' at position " + (pos - 1));
                }
            }
            return map;
        }

        private List<Object> parseArrayBody() {
            List<Object> list = new ArrayList<>();
            expect('[');
            skipWs();
            if (peek() == ']') {
                pos++;
                return list;
            }
            while (true) {
                skipWs();
                list.add(parseValue());
                skipWs();
                char c = next();
                if (c == ']') {
                    break;
                }
                if (c != ',') {
                    throw new JsonException("expected ',' or ']' at position " + (pos - 1));
                }
            }
            return list;
        }

        private String parseString() {
            expect('"');
            StringBuilder sb = new StringBuilder();
            while (true) {
                if (atEnd()) {
                    throw new JsonException("unterminated string");
                }
                char c = s.charAt(pos++);
                if (c == '"') {
                    break;
                }
                if (c == '\\') {
                    if (atEnd()) {
                        throw new JsonException("unterminated escape");
                    }
                    char e = s.charAt(pos++);
                    switch (e) {
                        case '"': sb.append('"'); break;
                        case '\\': sb.append('\\'); break;
                        case '/': sb.append('/'); break;
                        case 'b': sb.append('\b'); break;
                        case 'f': sb.append('\f'); break;
                        case 'n': sb.append('\n'); break;
                        case 'r': sb.append('\r'); break;
                        case 't': sb.append('\t'); break;
                        case 'u':
                            if (pos + 4 > s.length()) {
                                throw new JsonException("invalid unicode escape");
                            }
                            String hex = s.substring(pos, pos + 4);
                            try {
                                sb.append((char) Integer.parseInt(hex, 16));
                            } catch (NumberFormatException ex) {
                                throw new JsonException("invalid unicode escape: " + hex);
                            }
                            pos += 4;
                            break;
                        default:
                            throw new JsonException("invalid escape: \\" + e);
                    }
                } else {
                    sb.append(c);
                }
            }
            return sb.toString();
        }

        private Boolean parseBoolean() {
            if (s.startsWith("true", pos)) {
                pos += 4;
                return Boolean.TRUE;
            }
            if (s.startsWith("false", pos)) {
                pos += 5;
                return Boolean.FALSE;
            }
            throw new JsonException("invalid literal at position " + pos);
        }

        private Object parseNull() {
            if (s.startsWith("null", pos)) {
                pos += 4;
                return null;
            }
            throw new JsonException("invalid literal at position " + pos);
        }

        private Double parseNumber() {
            int start = pos;
            if (peek() == '-') {
                pos++;
            }
            while (pos < s.length()) {
                char c = s.charAt(pos);
                if (Character.isDigit(c) || c == '.' || c == 'e' || c == 'E'
                        || c == '+' || c == '-') {
                    pos++;
                } else {
                    break;
                }
            }
            String token = s.substring(start, pos);
            if (token.isEmpty()) {
                throw new JsonException("invalid value at position " + start);
            }
            try {
                return Double.parseDouble(token);
            } catch (NumberFormatException ex) {
                throw new JsonException("invalid number: " + token);
            }
        }

        private char peek() {
            if (atEnd()) {
                throw new JsonException("unexpected end of input");
            }
            return s.charAt(pos);
        }

        private char next() {
            char c = peek();
            pos++;
            return c;
        }

        private void expect(char expected) {
            char c = next();
            if (c != expected) {
                throw new JsonException(
                    "expected '" + expected + "' at position " + (pos - 1) + " but found '" + c + "'");
            }
        }
    }

    // ----- Writing -------------------------------------------------------

    public static String write(Object value) {
        StringBuilder sb = new StringBuilder();
        writeValue(sb, value);
        return sb.toString();
    }

    @SuppressWarnings("unchecked")
    private static void writeValue(StringBuilder sb, Object value) {
        if (value == null) {
            sb.append("null");
        } else if (value instanceof Map) {
            writeObject(sb, (Map<String, Object>) value);
        } else if (value instanceof List) {
            writeArray(sb, (List<Object>) value);
        } else if (value instanceof String) {
            writeString(sb, (String) value);
        } else if (value instanceof Boolean) {
            sb.append(value.toString());
        } else if (value instanceof Number) {
            writeNumber(sb, (Number) value);
        } else {
            // Fallback: treat as string.
            writeString(sb, value.toString());
        }
    }

    private static void writeObject(StringBuilder sb, Map<String, Object> map) {
        sb.append('{');
        boolean first = true;
        for (Map.Entry<String, Object> e : map.entrySet()) {
            if (!first) {
                sb.append(',');
            }
            first = false;
            writeString(sb, e.getKey());
            sb.append(':');
            writeValue(sb, e.getValue());
        }
        sb.append('}');
    }

    private static void writeArray(StringBuilder sb, List<Object> list) {
        sb.append('[');
        boolean first = true;
        for (Object item : list) {
            if (!first) {
                sb.append(',');
            }
            first = false;
            writeValue(sb, item);
        }
        sb.append(']');
    }

    private static void writeNumber(StringBuilder sb, Number n) {
        double d = n.doubleValue();
        if (d == Math.rint(d) && !Double.isInfinite(d)) {
            sb.append(Long.toString((long) d));
        } else {
            sb.append(n.toString());
        }
    }

    private static void writeString(StringBuilder sb, String str) {
        sb.append('"');
        for (int i = 0; i < str.length(); i++) {
            char c = str.charAt(i);
            switch (c) {
                case '"': sb.append("\\\""); break;
                case '\\': sb.append("\\\\"); break;
                case '\b': sb.append("\\b"); break;
                case '\f': sb.append("\\f"); break;
                case '\n': sb.append("\\n"); break;
                case '\r': sb.append("\\r"); break;
                case '\t': sb.append("\\t"); break;
                default:
                    if (c < 0x20) {
                        sb.append(String.format("\\u%04x", (int) c));
                    } else {
                        sb.append(c);
                    }
            }
        }
        sb.append('"');
    }
}
