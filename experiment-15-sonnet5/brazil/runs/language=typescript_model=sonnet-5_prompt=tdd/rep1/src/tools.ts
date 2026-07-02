import { formatISODate } from "./dates.js";
import { findMatchesByTeam, headToHead, canonicalMatches } from "./matchQueries.js";
import { teamRecord, compareTeams, type TeamRecord } from "./teamQueries.js";
import { topRatedPlayers } from "./playerQueries.js";
import { calculateStandings } from "./competitionQueries.js";
import { averageGoalsPerMatch, homeAwayWinRates, biggestWins } from "./statsQueries.js";
import { teamsMatch } from "./normalize.js";
import type { Match, Player } from "./types.js";

export interface AppData {
  matches: Match[];
  players: Player[];
}

function formatMatch(m: Match): string {
  const suffix = m.round ? ` Round ${m.round}` : m.stage ? ` - ${m.stage}` : "";
  return `${formatISODate(m.date)}: ${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam} (${m.competition}${suffix})`;
}

function formatSigned(value: number): string {
  return value >= 0 ? `+${value}` : `${value}`;
}

export interface SearchMatchesArgs {
  team: string;
  opponent?: string;
  competition?: string;
  season?: number;
  startDate?: string;
  endDate?: string;
  limit?: number;
}

export function searchMatchesTool(data: AppData, args: SearchMatchesArgs): string {
  const canonical = canonicalMatches(data.matches);
  const found = findMatchesByTeam(canonical, args.team, args);
  if (found.length === 0) return `No matches found for ${args.team}.`;

  const limited = args.limit !== undefined ? found.slice(0, args.limit) : found;
  const lines = [`Found ${found.length} match(es) for ${args.team}:`, ...limited.map(formatMatch)];

  if (args.opponent) {
    const h2h = headToHead(canonical, args.team, args.opponent);
    lines.push(
      "",
      `Head-to-head vs ${args.opponent}: ${args.team} ${h2h.teamAWins} win${h2h.teamAWins === 1 ? "" : "s"}, ` +
        `${args.opponent} ${h2h.teamBWins} win${h2h.teamBWins === 1 ? "" : "s"}, ${h2h.draws} draws`,
    );
  }

  return lines.join("\n");
}

export interface TeamRecordArgs {
  team: string;
  competition?: string;
  season?: number;
  venue?: "home" | "away" | "all";
}

function formatRecordLabel(args: { competition?: string; season?: number; venue?: "home" | "away" | "all" }): string {
  const parts: string[] = [];
  if (args.season !== undefined) parts.push(String(args.season));
  if (args.competition) parts.push(args.competition);
  if (args.venue && args.venue !== "all") parts.push(args.venue);
  return parts.length ? ` (${parts.join(", ")})` : "";
}

function formatRecordBody(record: TeamRecord): string[] {
  return [
    `- Matches: ${record.matchesPlayed}`,
    `- Wins: ${record.wins}, Draws: ${record.draws}, Losses: ${record.losses}`,
    `- Goals For: ${record.goalsFor}, Goals Against: ${record.goalsAgainst}`,
    `- Win rate: ${record.winRate.toFixed(1)}%`,
  ];
}

export function teamRecordTool(data: AppData, args: TeamRecordArgs): string {
  const record = teamRecord(canonicalMatches(data.matches), args.team, args);
  const label = formatRecordLabel(args);
  return [`${args.team} record${label}:`, ...formatRecordBody(record)].join("\n");
}

export interface CompareTeamsArgs {
  teamA: string;
  teamB: string;
  competition?: string;
  season?: number;
}

export function compareTeamsTool(data: AppData, args: CompareTeamsArgs): string {
  const comparison = compareTeams(canonicalMatches(data.matches), args.teamA, args.teamB, args);
  const h2h = comparison.headToHead;

  return [
    `${args.teamA} vs ${args.teamB} head-to-head:`,
    `- ${args.teamA} wins: ${h2h.teamAWins}`,
    `- ${args.teamB} wins: ${h2h.teamBWins}`,
    `- Draws: ${h2h.draws}`,
    "",
    `${args.teamA} record: ${comparison.teamA.matchesPlayed} matches, ${comparison.teamA.wins}W-${comparison.teamA.draws}D-${comparison.teamA.losses}L, GF ${comparison.teamA.goalsFor} GA ${comparison.teamA.goalsAgainst}`,
    `${args.teamB} record: ${comparison.teamB.matchesPlayed} matches, ${comparison.teamB.wins}W-${comparison.teamB.draws}D-${comparison.teamB.losses}L, GF ${comparison.teamB.goalsFor} GA ${comparison.teamB.goalsAgainst}`,
  ].join("\n");
}

export interface SearchPlayersArgs {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  limit?: number;
}

export function searchPlayersTool(data: AppData, args: SearchPlayersArgs): string {
  const found = topRatedPlayers(data.players, args);
  if (found.length === 0) return "No players found.";

  const lines = [
    `Found ${found.length} player(s):`,
    ...found.map(
      (p, i) => `${i + 1}. ${p.name} - Overall: ${p.overall ?? "N/A"}, Position: ${p.position ?? "N/A"}, Club: ${p.club}`,
    ),
  ];
  return lines.join("\n");
}

export interface CompetitionStandingsArgs {
  competition: string;
  season: number;
}

export function competitionStandingsTool(data: AppData, args: CompetitionStandingsArgs): string {
  const standings = calculateStandings(canonicalMatches(data.matches), args.competition, args.season);
  if (standings.length === 0) return `No standings available for ${args.competition} ${args.season}.`;

  const lines = [
    `${args.competition} ${args.season} Standings:`,
    ...standings.map(
      (row, i) =>
        `${i + 1}. ${row.team} - ${row.points} pts (${row.wins}W, ${row.draws}D, ${row.losses}L) GD ${formatSigned(row.goalDifference)}`,
    ),
  ];
  return lines.join("\n");
}

export interface DatasetStatisticsArgs {
  competition?: string;
  season?: number;
}

export function datasetStatisticsTool(data: AppData, args: DatasetStatisticsArgs): string {
  const relevant = canonicalMatches(data.matches).filter((m) => {
    if (args.competition && m.competition.toLowerCase() !== args.competition.toLowerCase()) return false;
    if (args.season !== undefined && m.season !== args.season) return false;
    return true;
  });

  const rates = homeAwayWinRates(relevant);
  const top = biggestWins(relevant, 5);

  const scope = args.competition || args.season !== undefined
    ? ` (${[args.competition, args.season].filter(Boolean).join(" ")})`
    : "";

  return [
    `Dataset statistics${scope}:`,
    `- Matches analyzed: ${relevant.length}`,
    `- Average goals per match: ${averageGoalsPerMatch(relevant).toFixed(2)}`,
    `- Home win rate: ${rates.homeWinRate.toFixed(1)}%, Away win rate: ${rates.awayWinRate.toFixed(1)}%, Draw rate: ${rates.drawRate.toFixed(1)}%`,
    "",
    "Biggest wins:",
    ...top.map((r, i) => `${i + 1}. ${formatMatch(r.match)} - margin ${r.margin}`),
  ].join("\n");
}

export interface PlayerClubContextArgs {
  name: string;
}

export function playerClubContextTool(data: AppData, args: PlayerClubContextArgs): string {
  const [player] = topRatedPlayers(data.players, { name: args.name, limit: 1 });
  if (!player) return `No player found matching "${args.name}".`;

  const record = teamRecord(canonicalMatches(data.matches), player.club);
  const lines = [
    `${player.name} - Overall: ${player.overall ?? "N/A"}, Position: ${player.position ?? "N/A"}, Club: ${player.club}`,
    "",
  ];

  if (record.matchesPlayed === 0) {
    lines.push(`No match data found for ${player.club} in the dataset.`);
  } else {
    lines.push(`${player.club} record:`, ...formatRecordBody(record));
  }

  return lines.join("\n");
}

export interface ListTeamCompetitionsArgs {
  team: string;
}

export function listTeamCompetitionsTool(data: AppData, args: ListTeamCompetitionsArgs): string {
  const competitions = new Set(
    canonicalMatches(data.matches)
      .filter((m) => teamsMatch(m.homeTeam, args.team) || teamsMatch(m.awayTeam, args.team))
      .map((m) => m.competition),
  );

  if (competitions.size === 0) return `No competitions found for ${args.team}.`;

  return [`${args.team} has played in:`, ...Array.from(competitions).sort().map((c) => `- ${c}`)].join("\n");
}
