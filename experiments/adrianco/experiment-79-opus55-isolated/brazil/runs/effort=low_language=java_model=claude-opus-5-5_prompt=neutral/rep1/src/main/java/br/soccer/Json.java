package br.soccer;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Minimal JSON reader/writer. Objects are {@code Map<String,Object>}, arrays are {@code List<Object>},
 * numbers are {@code Long} (integral) or {@code Double}.
 */
public final class Json {
    private final String s;
    private int i;

    private Json(String s) {
        this.s = s;
    }

    public static Object parse(String text) {
        Json p = new Json(text);
        p.ws();
        Object v = p.value();
        p.ws();
        if (p.i != p.s.length()) throw p.err("Trailing characters");
        return v;
    }

    private IllegalArgumentException err(String msg) {
        return new IllegalArgumentException(msg + " at position " + i);
    }

    private void ws() {
        while (i < s.length() && Character.isWhitespace(s.charAt(i))) i++;
    }

    private Object value() {
        if (i >= s.length()) throw err("Unexpected end of input");
        char c = s.charAt(i);
        switch (c) {
            case '{': return object();
            case '[': return array();
            case '"': return string();
            case 't': return literal("true", Boolean.TRUE);
            case 'f': return literal("false", Boolean.FALSE);
            case 'n': return literal("null", null);
            default: return number();
        }
    }

    private Object literal(String word, Object v) {
        if (!s.startsWith(word, i)) throw err("Unexpected token");
        i += word.length();
        return v;
    }

    private Map<String, Object> object() {
        Map<String, Object> m = new LinkedHashMap<>();
        i++;
        ws();
        if (peek() == '}') {
            i++;
            return m;
        }
        while (true) {
            ws();
            if (peek() != '"') throw err("Expected string key");
            String k = string();
            ws();
            if (peek() != ':') throw err("Expected ':'");
            i++;
            ws();
            m.put(k, value());
            ws();
            char c = peek();
            i++;
            if (c == '}') return m;
            if (c != ',') throw err("Expected ',' or '}'");
        }
    }

    private List<Object> array() {
        List<Object> l = new ArrayList<>();
        i++;
        ws();
        if (peek() == ']') {
            i++;
            return l;
        }
        while (true) {
            ws();
            l.add(value());
            ws();
            char c = peek();
            i++;
            if (c == ']') return l;
            if (c != ',') throw err("Expected ',' or ']'");
        }
    }

    private char peek() {
        if (i >= s.length()) throw err("Unexpected end of input");
        return s.charAt(i);
    }

    private String string() {
        StringBuilder b = new StringBuilder();
        i++;
        while (true) {
            char c = peek();
            i++;
            if (c == '"') return b.toString();
            if (c != '\\') {
                b.append(c);
                continue;
            }
            char e = peek();
            i++;
            switch (e) {
                case 'n': b.append('\n'); break;
                case 't': b.append('\t'); break;
                case 'r': b.append('\r'); break;
                case 'b': b.append('\b'); break;
                case 'f': b.append('\f'); break;
                case 'u':
                    if (i + 4 > s.length()) throw err("Bad unicode escape");
                    try {
                        b.append((char) Integer.parseInt(s.substring(i, i + 4), 16));
                    } catch (NumberFormatException ex) {
                        throw err("Bad unicode escape");
                    }
                    i += 4;
                    break;
                default: b.append(e);
            }
        }
    }

    private Object number() {
        int start = i;
        while (i < s.length() && "+-0123456789.eE".indexOf(s.charAt(i)) >= 0) i++;
        String t = s.substring(start, i);
        if (t.isEmpty()) throw err("Unexpected token");
        try {
            if (t.matches("-?\\d{1,18}")) return Long.parseLong(t);
            return Double.parseDouble(t);
        } catch (NumberFormatException ex) {
            throw err("Bad number");
        }
    }

    public static String write(Object v) {
        StringBuilder b = new StringBuilder();
        write(v, b);
        return b.toString();
    }

    private static void write(Object v, StringBuilder b) {
        if (v == null) {
            b.append("null");
        } else if (v instanceof Map<?, ?> m) {
            b.append('{');
            boolean first = true;
            for (Map.Entry<?, ?> e : m.entrySet()) {
                if (!first) b.append(',');
                first = false;
                quote(String.valueOf(e.getKey()), b);
                b.append(':');
                write(e.getValue(), b);
            }
            b.append('}');
        } else if (v instanceof Iterable<?> l) {
            b.append('[');
            boolean first = true;
            for (Object o : l) {
                if (!first) b.append(',');
                first = false;
                write(o, b);
            }
            b.append(']');
        } else if (v instanceof Number || v instanceof Boolean) {
            b.append(v);
        } else {
            quote(v.toString(), b);
        }
    }

    private static void quote(String str, StringBuilder b) {
        b.append('"');
        for (int k = 0; k < str.length(); k++) {
            char c = str.charAt(k);
            switch (c) {
                case '"': b.append("\\\""); break;
                case '\\': b.append("\\\\"); break;
                case '\n': b.append("\\n"); break;
                case '\r': b.append("\\r"); break;
                case '\t': b.append("\\t"); break;
                default:
                    if (c < 0x20) b.append(String.format("\\u%04x", (int) c));
                    else b.append(c);
            }
        }
        b.append('"');
    }
}
