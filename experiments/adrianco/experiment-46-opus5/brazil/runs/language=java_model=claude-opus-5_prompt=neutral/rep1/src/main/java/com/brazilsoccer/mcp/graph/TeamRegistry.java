package com.brazilsoccer.mcp.graph;

import com.brazilsoccer.mcp.model.Team;
import com.brazilsoccer.mcp.util.TextUtils;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;

/**
 * Builds and owns the canonical club nodes of the knowledge graph.
 *
 * <p>Loading happens in two phases. During <em>observation</em> every raw club spelling found in
 * any CSV file is normalised and counted. {@link #build()} then decides, per base name, whether
 * the state is part of the identity: {@code "atletico"} occurs with MG, PR and GO, so three nodes
 * ({@code atletico-mg}, {@code atletico-pr}, {@code atletico-go}) are created, whereas
 * {@code "palmeiras"} only ever occurs with SP and collapses into a single {@code palmeiras} node.
 * Spellings without a state are attached to the most frequent state of that base name.
 *
 * <p>After {@link #build()} the registry answers two questions: {@link #idFor} maps a raw CSV
 * spelling to its node id (used by the loaders) and {@link #search} resolves free-text user input
 * such as "flamengo", "Atletico MG" or "sao paulo" to candidate clubs (used by the MCP tools).
 */
public final class TeamRegistry {

    private static final class Observation {
        final String base;
        final String state;
        int count;
        final Map<String, Integer> displayCandidates = new LinkedHashMap<>();
        final Set<String> rawNames = new TreeSet<>();

        Observation(String base, String state) {
            this.base = base;
            this.state = state;
        }
    }

    private final Map<String, Observation> observations = new LinkedHashMap<>();
    private final Map<String, Team> teamsById = new LinkedHashMap<>();
    private final Map<String, String> rawNameToId = new HashMap<>();
    private final Map<String, List<Team>> teamsByBase = new TreeMap<>();
    private final Map<String, String> teamIdToBase = new HashMap<>();
    private boolean built;

    /** Registers one raw club spelling (phase 1). */
    public void observe(String rawName, String stateHint) {
        if (rawName == null || rawName.isBlank()) {
            return;
        }
        TeamNameNormalizer.NormalizedName normalized = TeamNameNormalizer.normalize(rawName, stateHint);
        if (normalized.base().isBlank()) {
            return;
        }
        String key = normalized.base() + "|" + (normalized.state() == null ? "" : normalized.state());
        Observation observation = observations.computeIfAbsent(key,
                k -> new Observation(normalized.base(), normalized.state()));
        observation.count++;
        observation.rawNames.add(rawName.trim());
        observation.displayCandidates.merge(normalized.display(), 1, Integer::sum);
    }

    /** Creates the canonical club nodes from everything observed so far (phase 2). */
    public void build() {
        Map<String, List<Observation>> byBase = new LinkedHashMap<>();
        for (Observation observation : observations.values()) {
            byBase.computeIfAbsent(observation.base, k -> new ArrayList<>()).add(observation);
        }
        for (Map.Entry<String, List<Observation>> entry : byBase.entrySet()) {
            String base = entry.getKey();
            List<Observation> group = entry.getValue();
            Map<String, Integer> stateCounts = new LinkedHashMap<>();
            for (Observation observation : group) {
                if (observation.state != null) {
                    stateCounts.merge(observation.state, observation.count, Integer::sum);
                }
            }
            boolean ambiguous = stateCounts.size() > 1;
            String majorityState = stateCounts.entrySet().stream()
                    .max(Map.Entry.comparingByValue())
                    .map(Map.Entry::getKey)
                    .orElse(null);

            for (Observation observation : group) {
                String state = observation.state != null ? observation.state : majorityState;
                String id = ambiguous && state != null
                        ? base.replace(' ', '-') + "-" + state.toLowerCase(Locale.ROOT)
                        : base.replace(' ', '-');
                Team team = teamsById.get(id);
                if (team == null) {
                    team = new Team(id, chooseDisplay(base, state, observation), state);
                    teamsById.put(id, team);
                    teamsByBase.computeIfAbsent(base, k -> new ArrayList<>()).add(team);
                    teamIdToBase.put(id, base);
                } else {
                    String candidate = chooseDisplay(base, state, observation);
                    if (candidate.length() < team.displayName().length()
                            && TeamNameNormalizer.preferredDisplayName(base, state) == null) {
                        team.setDisplayName(candidate);
                    }
                }
                for (String raw : observation.rawNames) {
                    team.addAlias(raw);
                    rawNameToId.put(rawKey(raw, observation.state), id);
                    rawNameToId.putIfAbsent(rawKey(raw, null), id);
                }
            }
        }
        built = true;
    }

    private String chooseDisplay(String base, String state, Observation observation) {
        String preferred = TeamNameNormalizer.preferredDisplayName(base, state);
        if (preferred != null) {
            return preferred;
        }
        return observation.displayCandidates.entrySet().stream()
                .filter(e -> e.getKey() != null && !e.getKey().isBlank())
                .max(Comparator
                        .<Map.Entry<String, Integer>>comparingInt(Map.Entry::getValue)
                        .thenComparingInt(e -> accentCount(e.getKey()))
                        .thenComparing(e -> -e.getKey().length()))
                .map(Map.Entry::getKey)
                .orElse(base);
    }

    private static int accentCount(String value) {
        int count = 0;
        for (int i = 0; i < value.length(); i++) {
            if (value.charAt(i) > 127) {
                count++;
            }
        }
        return count;
    }

    private static String rawKey(String rawName, String stateHint) {
        return TextUtils.simplify(rawName) + "#" + (stateHint == null ? "" : stateHint);
    }

    /** Maps a raw CSV spelling to a canonical node id (phase 3, used by the loaders). */
    public String idFor(String rawName, String stateHint) {
        requireBuilt();
        TeamNameNormalizer.NormalizedName normalized = TeamNameNormalizer.normalize(rawName, stateHint);
        String id = rawNameToId.get(rawKey(rawName, normalized.state()));
        if (id != null) {
            return id;
        }
        id = rawNameToId.get(rawKey(rawName, null));
        if (id != null) {
            return id;
        }
        return search(rawName).stream().findFirst().map(Team::id).orElse(null);
    }

    public Optional<Team> team(String id) {
        return Optional.ofNullable(teamsById.get(id));
    }

    public Collection<Team> teams() {
        return teamsById.values();
    }

    public int size() {
        return teamsById.size();
    }

    /**
     * Resolves free-text user input to candidate clubs, best match first. Exact canonical matches
     * come first, then prefix matches, then substring matches; ties are broken by how much data
     * the club has in the graph (clubs with many matches win over obscure namesakes).
     */
    public List<Team> search(String query) {
        requireBuilt();
        if (query == null || query.isBlank()) {
            return List.of();
        }
        TeamNameNormalizer.NormalizedName normalized = TeamNameNormalizer.normalize(query, null);
        String base = normalized.base();
        String state = normalized.state();

        // Clubs sharing the base name, with the ones matching the requested state first: a query
        // for "Botafogo" answers Botafogo-RJ but still reports its namesakes from SP and PB.
        List<Team> sameBase = new ArrayList<>(teamsByBase.getOrDefault(base, List.of()));
        if (!sameBase.isEmpty()) {
            return preferState(sortByRelevance(sameBase), state);
        }

        String rawId = rawNameToId.get(rawKey(query, state));
        if (rawId == null) {
            rawId = rawNameToId.get(rawKey(query, null));
        }
        if (rawId != null) {
            return List.of(teamsById.get(rawId));
        }

        List<Team> prefix = new ArrayList<>();
        List<Team> contains = new ArrayList<>();
        for (Map.Entry<String, List<Team>> entry : teamsByBase.entrySet()) {
            String candidateBase = entry.getKey();
            if (candidateBase.equals(base)) {
                continue;
            }
            if (candidateBase.startsWith(base) || base.startsWith(candidateBase)) {
                prefix.addAll(entry.getValue());
            } else if (candidateBase.contains(base)) {
                contains.addAll(entry.getValue());
            }
        }
        List<Team> result = new ArrayList<>(sortByRelevance(prefix));
        result.addAll(sortByRelevance(contains));
        return preferState(result, state);
    }

    /** Moves the clubs of the requested state to the front, keeping the others as alternatives. */
    private static List<Team> preferState(List<Team> teams, String state) {
        if (state == null) {
            return teams;
        }
        List<Team> ordered = new ArrayList<>(teams.stream().filter(t -> state.equals(t.state())).toList());
        teams.stream().filter(t -> !state.equals(t.state())).forEach(ordered::add);
        return ordered;
    }

    /** Best single match for a user supplied club name. */
    public Optional<Team> resolve(String query) {
        return search(query).stream().findFirst();
    }

    /** Base name (state independent key) of a node, used to group namesakes. */
    public String baseOf(String teamId) {
        return teamIdToBase.get(teamId);
    }

    private List<Team> sortByRelevance(List<Team> teams) {
        List<Team> copy = new ArrayList<>(teams);
        copy.sort(Comparator.comparingInt(Team::matchCount).reversed()
                .thenComparing(Comparator.comparingInt(Team::playerCount).reversed())
                .thenComparing(Team::displayName));
        return copy;
    }

    private void requireBuilt() {
        if (!built) {
            throw new IllegalStateException("TeamRegistry.build() must be called before querying it");
        }
    }
}
