package com.brazilsoccer.mcp.tools;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Tiny builder for the JSON Schema objects advertised as MCP tool input schemas. */
public final class Schemas {

    private final Map<String, Object> properties = new LinkedHashMap<>();
    private final List<String> required = new ArrayList<>();

    private Schemas() {
    }

    public static Schemas object() {
        return new Schemas();
    }

    /** Schema for a tool that takes no arguments. */
    public static Map<String, Object> empty() {
        return object().build();
    }

    public Schemas string(String name, String description) {
        properties.put(name, Map.of("type", "string", "description", description));
        return this;
    }

    public Schemas enumeration(String name, String description, List<String> values) {
        properties.put(name, Map.of("type", "string", "description", description, "enum", values));
        return this;
    }

    public Schemas integer(String name, String description) {
        properties.put(name, Map.of("type", "integer", "description", description));
        return this;
    }

    public Schemas bool(String name, String description) {
        properties.put(name, Map.of("type", "boolean", "description", description));
        return this;
    }

    public Schemas integerArray(String name, String description) {
        properties.put(name, Map.of(
                "type", "array",
                "description", description,
                "items", Map.of("type", "integer")));
        return this;
    }

    public Schemas require(String... names) {
        required.addAll(List.of(names));
        return this;
    }

    public Map<String, Object> build() {
        Map<String, Object> schema = new LinkedHashMap<>();
        schema.put("type", "object");
        schema.put("properties", Map.copyOf(properties));
        schema.put("required", List.copyOf(required));
        schema.put("additionalProperties", false);
        return Map.copyOf(schema);
    }
}
