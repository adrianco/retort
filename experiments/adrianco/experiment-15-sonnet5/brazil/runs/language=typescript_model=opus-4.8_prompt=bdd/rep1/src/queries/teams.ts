/**
 * Team-centric queries: win/draw/loss records, goals for/against, and
 * home vs away splits, computed from played matches.
 */
import { teamMatches } from "../normalize.js";
import type { Match, TeamRecord } from "../types.js";
import { filterMatches, type MatchFilter } from "./filters.js";

export interface TeamStats extends TeamRecord {
  goalDifference: number;
  winRate: number;
  home: TeamRecord;
  away: TeamRecord;
  competitions: string[];
}

function emptyRecord(team: string): TeamRecord {
  return {
    team,
    played: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    goalsFor: 0,
    goalsAgainst: 0,
    points: 0,
  };
}

function applyResult(record: TeamRecord, scored: number, conceded: number): void {
  record.played += 1;
  record.goalsFor += scored;
  record.goalsAgainst += conceded;
  if (scored > conceded) {
    record.wins += 1;
    record.points += 3;
  } else if (scored === conceded) {
    record.draws += 1;
    record.points += 1;
  } else {
    record.losses += 1;
  }
}

/**
 * Aggregate a team's performance over the matches selected by `filter`.
 * `filter.team` is set from `team`, so callers typically pass season and/or
 * competition constraints in `filter`.
 */
export function teamStats(all: Match[], team: string, filter: MatchFilter = {}): TeamStats {
  const matches = filterMatches(all, { ...filter, team, playedOnly: true });

  const total = emptyRecord(team);
  const home = emptyRecord(team);
  const away = emptyRecord(team);
  const competitions = new Set<string>();

  for (const m of matches) {
    competitions.add(m.competition);
    const homeGoals = m.homeGoals as number;
    const awayGoals = m.awayGoals as number;
    if (teamMatches(m.homeTeam, team)) {
      applyResult(total, homeGoals, awayGoals);
      applyResult(home, homeGoals, awayGoals);
    } else {
      applyResult(total, awayGoals, homeGoals);
      applyResult(away, awayGoals, homeGoals);
    }
  }

  return {
    ...total,
    goalDifference: total.goalsFor - total.goalsAgainst,
    winRate: total.played > 0 ? total.wins / total.played : 0,
    home,
    away,
    competitions: [...competitions].sort(),
  };
}
