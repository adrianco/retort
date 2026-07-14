package com.soccer.mcp.service;

import java.text.Normalizer;
import java.util.regex.Pattern;

/**
 * Normalizes team names for consistent matching.
 * Strips state suffixes (-SP, -RJ, etc.) and handles accent variants.
 */
public class TeamNameNormalizer {

    // Pattern to strip state suffix like -SP, -RJ, -MG, " - SP", " - rj", etc.
    private static final Pattern STATE_SUFFIX_PATTERN =
            Pattern.compile("\\s*-\\s*[A-Za-z]{2}\\s*$");

    /**
     * Normalizes a team name by stripping state suffix and trimming whitespace.
     */
    public String normalize(String teamName) {
        if (teamName == null) return "";
        String result = STATE_SUFFIX_PATTERN.matcher(teamName.trim()).replaceAll("");
        return result.trim();
    }

    /**
     * Returns a canonical (lowercase, accent-free) version of a team name for comparison.
     */
    public String canonical(String teamName) {
        String normalized = normalize(teamName);
        return removeAccents(normalized.toLowerCase());
    }

    /**
     * Checks if a stored team name matches a query string.
     * Matching is: case-insensitive, accent-insensitive, partial (contains).
     */
    public boolean matches(String storedName, String query) {
        if (storedName == null || query == null) return false;
        String storedCanonical = canonical(storedName);
        String queryCanonical = canonical(query);
        return storedCanonical.contains(queryCanonical) || queryCanonical.contains(storedCanonical);
    }

    /**
     * Remove accents from a string using Unicode normalization.
     */
    private String removeAccents(String input) {
        if (input == null) return "";
        String normalized = Normalizer.normalize(input, Normalizer.Form.NFD);
        return normalized.replaceAll("\\p{InCombiningDiacriticalMarks}+", "");
    }
}
