/*
 * ============================================================================
 * CompetitionService.java
 * ============================================================================
 * Context:
 *   Implements the spec's "Competition Queries" category: league standings
 *   calculated from match results for a given competition and season.
 *
 *   De-duplication: the Brasileirão appears in three overlapping files
 *   (Brasileirao_Matches.csv 2012-2022, novo_campeonato_brasileiro.csv
 *   2003-2019, BR-Football Serie A 2014-2023). Naively pooling them would
 *   double- or triple-count fixtures and corrupt the table. For each season we
 *   therefore pick the single source file that contributed the most matches and
 *   compute the standings from that source alone. The same helper is reused by
 *   StatsService so its league averages are not skewed by duplicates.
 * ============================================================================
 */
package com.brazilsoccer.mcp.query;

import com.brazilsoccer.mcp.data.Competitions;
import com.brazilsoccer.mcp.data.DataStore;
import com.brazilsoccer.mcp.model.Match;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Query service for competition standings. */
public final class CompetitionService {

    private final DataStore store;

    public CompetitionService(DataStore store) {
        this.store = store;
    }

    /**
     * Calculate the final standings for a competition and season, ordered by
     * points, then goal difference, then goals scored. The list index + 1 is
     * each team's rank.
     */
    public List<TeamRecord> standings(String competition, int season) {
        // store.matches() is already de-duplicated to one source per
        // (competition, season), so a straight filter cannot double-count.
        Map<String, TeamRecord> table = new HashMap<>();
        for (Match m : store.matches()) {
            if (m.season() != season) continue;
            if (!Competitions.matches(m.competition(), competition)) continue;
            if (!m.hasScore()) continue;
            TeamRecord home = table.computeIfAbsent(m.homeTeamKey(), k -> new TeamRecord(m.homeTeam()));
            TeamRecord away = table.computeIfAbsent(m.awayTeamKey(), k -> new TeamRecord(m.awayTeam()));
            home.add(m.homeGoal(), m.awayGoal());
            away.add(m.awayGoal(), m.homeGoal());
        }

        List<TeamRecord> rows = new ArrayList<>(table.values());
        rows.sort(Comparator
                .comparingInt(TeamRecord::points).reversed()
                .thenComparing(Comparator.comparingInt(TeamRecord::goalDifference).reversed())
                .thenComparing(Comparator.comparingInt((TeamRecord r) -> r.goalsFor).reversed())
                .thenComparing(r -> r.team));
        return rows;
    }
}
