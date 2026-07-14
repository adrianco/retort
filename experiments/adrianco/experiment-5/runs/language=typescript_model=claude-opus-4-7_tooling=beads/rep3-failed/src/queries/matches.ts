import { DataStore, Match, Competition } from '../data/types.js';
import { teamMatches, formatDate } from '../data/normalize.js';

export interface MatchFilter {
  team?: string;
  homeTeam?: string;
  awayTeam?: string;
  opponentTeam?: string; // matches between team & opponent
  competition?: Competition;
  season?: number;
  startDate?: Date;
  endDate?: Date;
  stage?: string;
  limit?: number;
}

export function findMatches(store: DataStore, f: MatchFilter): Match[] {
  let results = store.matches;

  if (f.competition) {
    results = results.filter((m) => m.competition === f.competition);
  }
  if (f.season !== undefined) {
    results = results.filter((m) => m.season === f.season);
  }
  if (f.startDate) {
    results = results.filter((m) => m.date >= f.startDate!);
  }
  if (f.endDate) {
    results = results.filter((m) => m.date <= f.endDate!);
  }
  if (f.stage) {
    results = results.filter(
      (m) => m.stage && m.stage.toLowerCase().includes(f.stage!.toLowerCase()),
    );
  }
  if (f.homeTeam) {
    results = results.filter((m) => teamMatches(m.homeTeam, f.homeTeam!));
  }
  if (f.awayTeam) {
    results = results.filter((m) => teamMatches(m.awayTeam, f.awayTeam!));
  }
  if (f.team) {
    results = results.filter(
      (m) => teamMatches(m.homeTeam, f.team!) || teamMatches(m.awayTeam, f.team!),
    );
  }
  if (f.opponentTeam && f.team) {
    results = results.filter(
      (m) =>
        (teamMatches(m.homeTeam, f.team!) && teamMatches(m.awayTeam, f.opponentTeam!)) ||
        (teamMatches(m.awayTeam, f.team!) && teamMatches(m.homeTeam, f.opponentTeam!)),
    );
  }

  // Sort by date desc
  results = [...results].sort((a, b) => b.date.getTime() - a.date.getTime());

  if (f.limit !== undefined && f.limit > 0) {
    results = results.slice(0, f.limit);
  }
  return results;
}

export function formatMatch(m: Match): string {
  const dateStr = formatDate(m.date);
  const ctx: string[] = [m.competition];
  if (m.season) ctx.push(String(m.season));
  if (m.round !== undefined && m.round !== '') ctx.push(`Round ${m.round}`);
  if (m.stage) ctx.push(m.stage);
  return `${dateStr}: ${m.homeTeamRaw} ${m.homeGoals}-${m.awayGoals} ${m.awayTeamRaw} (${ctx.join(', ')})`;
}

export interface HeadToHead {
  team: string;
  opponent: string;
  totalMatches: number;
  teamWins: number;
  opponentWins: number;
  draws: number;
  teamGoals: number;
  opponentGoals: number;
}

export function headToHead(store: DataStore, team: string, opponent: string): HeadToHead {
  const matches = findMatches(store, { team, opponentTeam: opponent });
  let teamWins = 0, opponentWins = 0, draws = 0;
  let teamGoals = 0, opponentGoals = 0;
  for (const m of matches) {
    const teamIsHome = teamMatches(m.homeTeam, team);
    const tG = teamIsHome ? m.homeGoals : m.awayGoals;
    const oG = teamIsHome ? m.awayGoals : m.homeGoals;
    teamGoals += tG;
    opponentGoals += oG;
    if (tG > oG) teamWins++;
    else if (oG > tG) opponentWins++;
    else draws++;
  }
  return {
    team,
    opponent,
    totalMatches: matches.length,
    teamWins,
    opponentWins,
    draws,
    teamGoals,
    opponentGoals,
  };
}
