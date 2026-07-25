package com.brazilsoccer.mcp.tools;

import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Typed, forgiving accessor over the raw MCP argument map.
 *
 * <p>LLM clients happily send {@code "2019"} where an integer is expected (and the other way
 * round), so every getter accepts both representations and reports a helpful message when the
 * value really cannot be used.
 */
public final class ToolArguments {

    private final Map<String, Object> arguments;

    public ToolArguments(Map<String, Object> arguments) {
        this.arguments = arguments == null ? Map.of() : arguments;
    }

    public static ToolArguments of(Map<String, Object> arguments) {
        return new ToolArguments(arguments);
    }

    public boolean has(String name) {
        Object value = arguments.get(name);
        return value != null && !(value instanceof String string && string.isBlank());
    }

    public String string(String name) {
        Object value = arguments.get(name);
        if (value == null) {
            return null;
        }
        String text = String.valueOf(value).trim();
        return text.isEmpty() ? null : text;
    }

    public String string(String name, String fallback) {
        String value = string(name);
        return value == null ? fallback : value;
    }

    public String requireString(String name) {
        String value = string(name);
        if (value == null) {
            throw new ToolException("Missing required argument '" + name + "'.");
        }
        return value;
    }

    public Integer integer(String name) {
        Object value = arguments.get(name);
        if (value == null) {
            return null;
        }
        if (value instanceof Number number) {
            return number.intValue();
        }
        String text = String.valueOf(value).trim();
        if (text.isEmpty()) {
            return null;
        }
        try {
            return (int) Double.parseDouble(text);
        } catch (NumberFormatException e) {
            throw new ToolException("Argument '" + name + "' must be a number but was '" + text + "'.");
        }
    }

    public int integer(String name, int fallback) {
        Integer value = integer(name);
        return value == null ? fallback : value;
    }

    public int positiveInt(String name, int fallback, int max) {
        int value = integer(name, fallback);
        if (value <= 0) {
            throw new ToolException("Argument '" + name + "' must be greater than zero.");
        }
        return Math.min(value, max);
    }

    public boolean bool(String name, boolean fallback) {
        Object value = arguments.get(name);
        if (value == null) {
            return fallback;
        }
        if (value instanceof Boolean flag) {
            return flag;
        }
        return Boolean.parseBoolean(String.valueOf(value).trim());
    }

    public LocalDate date(String name) {
        String value = string(name);
        if (value == null) {
            return null;
        }
        try {
            return LocalDate.parse(value);
        } catch (DateTimeParseException e) {
            throw new ToolException("Argument '" + name + "' must be an ISO date (YYYY-MM-DD) but was '" + value + "'.");
        }
    }

    /** Accepts a JSON array, a single value or a comma separated string. */
    public List<Integer> integerList(String name) {
        Object value = arguments.get(name);
        if (value == null) {
            return List.of();
        }
        List<Integer> result = new ArrayList<>();
        if (value instanceof List<?> list) {
            for (Object item : list) {
                result.add(parseInteger(name, item));
            }
            return result;
        }
        for (String part : String.valueOf(value).split("[,;\\s]+")) {
            if (!part.isBlank()) {
                result.add(parseInteger(name, part));
            }
        }
        return result;
    }

    private static Integer parseInteger(String name, Object item) {
        if (item instanceof Number number) {
            return number.intValue();
        }
        try {
            return (int) Double.parseDouble(String.valueOf(item).trim());
        } catch (NumberFormatException e) {
            throw new ToolException("Argument '" + name + "' must contain numbers but had '" + item + "'.");
        }
    }

    public Map<String, Object> raw() {
        return arguments;
    }
}
