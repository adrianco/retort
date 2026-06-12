package com.braziliansoccer.mcp.service;

public class TeamNameNormalizer {
    public String normalize(String name) {
        if (name == null) return "";
        int dashIdx = name.lastIndexOf('-');
        if (dashIdx > 0) {
            String suffix = name.substring(dashIdx + 1);
            if (suffix.matches("[A-Z]{2,3}")) return name.substring(0, dashIdx).trim();
        }
        return name.trim();
    }

    public boolean matches(String teamName, String query) {
        if (teamName == null || query == null) return false;
        return normalize(teamName).toLowerCase().contains(query.toLowerCase());
    }
}
