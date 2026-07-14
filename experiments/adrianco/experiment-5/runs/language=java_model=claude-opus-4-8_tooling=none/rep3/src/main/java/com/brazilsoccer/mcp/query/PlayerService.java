/*
 * ============================================================================
 * PlayerService.java
 * ============================================================================
 * Context:
 *   Implements the spec's "Player Queries" category over the FIFA player
 *   database: search by name, filter by nationality and/or club, optionally by
 *   position and minimum overall rating, sorted by overall rating descending.
 *   Name/club/nationality matching is accent-insensitive and substring-based
 *   so "neymar" finds "Neymar Jr" and "Sao Paulo" finds "São Paulo".
 * ============================================================================
 */
package com.brazilsoccer.mcp.query;

import com.brazilsoccer.mcp.data.DataStore;
import com.brazilsoccer.mcp.data.TeamNames;
import com.brazilsoccer.mcp.model.Player;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/** Query service for FIFA player lookups. */
public final class PlayerService {

    private final DataStore store;

    public PlayerService(DataStore store) {
        this.store = store;
    }

    /** Criteria for {@link #search(Criteria)}; all fields optional/nullable. */
    public static final class Criteria {
        public String name;
        public String nationality;
        public String club;
        public String position;
        public Integer minOverall;
        public int limit = 25;       // 0 or negative = unlimited
    }

    /** Find players satisfying every supplied criterion, best-rated first. */
    public List<Player> search(Criteria c) {
        String nameNorm = c.name == null ? null : TeamNames.normalize(c.name);
        String natNorm = c.nationality == null ? null : TeamNames.normalize(c.nationality);
        String clubKey = c.club == null ? null : TeamNames.key(c.club);
        String posNorm = c.position == null ? null : TeamNames.normalize(c.position);

        List<Player> out = new ArrayList<>();
        for (Player p : store.players()) {
            if (nameNorm != null && !TeamNames.normalize(p.name()).contains(nameNorm)) continue;
            if (natNorm != null && !p.nationalityKey().contains(natNorm)) continue;
            if (clubKey != null && !MatchService.keyMatches(p.clubKey(), clubKey)) continue;
            if (posNorm != null) {
                String pos = p.position() == null ? "" : TeamNames.normalize(p.position());
                if (!pos.equals(posNorm)) continue;
            }
            if (c.minOverall != null && (p.overall() == null || p.overall() < c.minOverall)) continue;
            out.add(p);
        }

        out.sort(Comparator.comparing(
                (Player p) -> p.overall() == null ? Integer.MIN_VALUE : p.overall()).reversed());

        if (c.limit > 0 && out.size() > c.limit) {
            return new ArrayList<>(out.subList(0, c.limit));
        }
        return out;
    }
}
