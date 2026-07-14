package com.brsoccer.mcp.model;

public enum Competition {
    BRASILEIRAO("Brasileirão Serie A"),
    COPA_DO_BRASIL("Copa do Brasil"),
    LIBERTADORES("Copa Libertadores"),
    EXTENDED("Extended Match Statistics"),
    HISTORICAL_BRASILEIRAO("Historical Brasileirão (2003-2019)");

    private final String displayName;

    Competition(String displayName) {
        this.displayName = displayName;
    }

    public String getDisplayName() {
        return displayName;
    }

    public static Competition fromString(String name) {
        if (name == null) return null;
        String n = name.toLowerCase();
        if (n.contains("libertadores")) return LIBERTADORES;
        if (n.contains("copa") || n.contains("cup")) return COPA_DO_BRASIL;
        if (n.contains("brasileirao") || n.contains("brasileirão") || n.contains("serie a")) return BRASILEIRAO;
        return null;
    }
}
