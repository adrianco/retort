package com.brazilsoccer.mcp.model;

import java.util.Set;
import java.util.TreeSet;

/**
 * A club node of the knowledge graph.
 *
 * <p>{@code id} is the canonical, accent-free key produced by the team name normaliser (for
 * example {@code atletico-mg}); {@code displayName} is the nicest spelling seen in the data;
 * {@code aliases} keeps every raw spelling that mapped onto this node so that queries can be
 * explained back to the user.
 */
public final class Team {

    private final String id;
    private String displayName;
    private final String state;
    private final Set<String> aliases = new TreeSet<>();
    private int matchCount;
    private int playerCount;

    public Team(String id, String displayName, String state) {
        this.id = id;
        this.displayName = displayName;
        this.state = state;
    }

    public String id() {
        return id;
    }

    public String displayName() {
        return displayName;
    }

    public void setDisplayName(String displayName) {
        this.displayName = displayName;
    }

    /** Two letter Brazilian state (UF) or country code for foreign clubs; may be {@code null}. */
    public String state() {
        return state;
    }

    public Set<String> aliases() {
        return aliases;
    }

    public void addAlias(String alias) {
        if (alias != null && !alias.isBlank()) {
            aliases.add(alias.trim());
        }
    }

    public int matchCount() {
        return matchCount;
    }

    public void incrementMatchCount() {
        matchCount++;
    }

    public int playerCount() {
        return playerCount;
    }

    public void incrementPlayerCount() {
        playerCount++;
    }

    /** Display name including the state suffix when one is known, e.g. {@code Botafogo (RJ)}. */
    public String qualifiedName() {
        return state == null || state.isBlank() ? displayName : displayName + " (" + state + ")";
    }

    @Override
    public String toString() {
        return qualifiedName();
    }
}
