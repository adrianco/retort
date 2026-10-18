/** Plain-text renderers for query results, shaped like the spec's example answers. */
import type { Match, Player } from "./model.js";
import type { ClubSummary, HeadToHead, MatchSearchResult, MatchStats, TeamRecord, StandingRow } from "./queries.js";

const pct = (fraction: number): string => `${(fraction * 100).toFixed(1)}%`;

export function formatMatchLine(m: Match): string {
  const round = m.round ? ` (${m.competition}, ${m.round})` : ` (${m.competition})`;
  return `- ${m.date}: ${m.home} ${m.homeGoals}-${m.awayGoals} ${m.away}${round}`;
}

export function formatMatchSearch(result: MatchSearchResult): string {
  if (result.total === 0) return "No matches found for these criteria.";
  const shown = result.matches.map(formatMatchLine);
  const more = result.total - result.matches.length;
  return [
    `Matches found: ${result.total}`,
    ...shown,
    ...(more > 0 ? [`... (${more} more matches in dataset)`] : []),
  ].join("\n");
}

export function formatRecord(title: string, rec: TeamRecord): string {
  if (rec.matches === 0) return `${title}\n- No matches found in dataset.`;
  return [
    title,
    `- Matches: ${rec.matches}`,
    `- Wins: ${rec.wins}, Draws: ${rec.draws}, Losses: ${rec.losses}`,
    `- Goals For: ${rec.goalsFor}, Goals Against: ${rec.goalsAgainst}`,
    `- Win rate: ${pct(rec.winRate)}`,
  ].join("\n");
}

export function formatHeadToHead(h: HeadToHead): string {
  if (h.record.matches === 0) return `${h.teamA} vs ${h.teamB}: no meetings found in dataset.`;
  const r = h.record;
  return [
    `${h.teamA} vs ${h.teamB} head-to-head in dataset (${r.matches} matches):`,
    `${h.teamA} ${r.wins} wins, ${h.teamB} ${h.winsB} wins, ${r.draws} draws`,
    `Goals: ${h.teamA} ${r.goalsFor} - ${r.goalsAgainst} ${h.teamB}`,
    "Most recent:",
    ...h.matches.slice(0, 5).map(formatMatchLine),
  ].join("\n");
}

export function formatStandings(title: string, rows: StandingRow[]): string {
  if (rows.length === 0) return `${title}\nNo matches found for this season and competition.`;
  const lines = rows.map(
    (r, i) =>
      `${i + 1}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L) ` +
      `GF ${r.goalsFor} GA ${r.goalsAgainst} GD ${r.goalDifference > 0 ? "+" : ""}${r.goalDifference}`,
  );
  return [title, ...lines].join("\n");
}

export function formatPlayers(players: Player[]): string {
  if (players.length === 0) return "No players found for these criteria.";
  return players
    .map(
      (p, i) =>
        `${i + 1}. ${p.name} - Overall: ${p.overall}, Position: ${p.position}, ` +
        `Club: ${p.club || "-"}, Nationality: ${p.nationality}, Age: ${p.age}`,
    )
    .join("\n");
}

export function formatClubSummary(rows: ClubSummary[]): string {
  if (rows.length === 0) return "No players found for these criteria.";
  return rows
    .map((r) => `- ${r.club}: ${r.players} players (avg overall: ${r.averageOverall})`)
    .join("\n");
}

export function formatMatchStats(title: string, s: MatchStats): string {
  if (s.matches === 0) return `${title}\nNo matches found for these criteria.`;
  const lines = [
    title,
    `Matches: ${s.matches}`,
    `Average goals per match: ${s.averageGoalsPerMatch.toFixed(2)}`,
    `Home win rate: ${pct(s.homeWinRate)}, Draw rate: ${pct(s.drawRate)}, Away win rate: ${pct(s.awayWinRate)}`,
  ];
  if (s.biggestWins.length > 0) {
    lines.push("Biggest victories:", ...s.biggestWins.map(formatMatchLine));
  }
  return lines.join("\n");
}
