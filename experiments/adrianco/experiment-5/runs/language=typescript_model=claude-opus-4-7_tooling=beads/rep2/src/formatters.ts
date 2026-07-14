import type { Match, Player, TeamRecord, HeadToHead } from "./types.js";

export function formatMatch(m: Match): string {
  const score = m.homeGoal !== null && m.awayGoal !== null
    ? `${m.homeGoal}-${m.awayGoal}`
    : "?-?";
  const date = m.date ?? "unknown date";
  const round = m.round ? ` Round ${m.round}` : "";
  const stage = m.stage ? ` ${m.stage}` : "";
  return `${date}: ${m.homeTeam} ${score} ${m.awayTeam} (${m.competition}${round}${stage})`;
}

export function formatMatches(ms: Match[], limit?: number): string {
  if (ms.length === 0) return "No matches found.";
  const slice = limit ? ms.slice(0, limit) : ms;
  return slice.map((m) => "- " + formatMatch(m)).join("\n");
}

export function formatTeamRecord(r: TeamRecord, title?: string): string {
  const pct = (r.winRate * 100).toFixed(1);
  return [
    title ? `${title}:` : `${r.team}:`,
    `- Matches: ${r.matches}`,
    `- Wins: ${r.wins}, Draws: ${r.draws}, Losses: ${r.losses}`,
    `- Goals For: ${r.goalsFor}, Goals Against: ${r.goalsAgainst} (GD ${r.goalDifference >= 0 ? "+" : ""}${r.goalDifference})`,
    `- Points: ${r.points}`,
    `- Win rate: ${pct}%`,
  ].join("\n");
}

export function formatHeadToHead(h: HeadToHead): string {
  return [
    `${h.teamA} vs ${h.teamB}:`,
    `- Matches: ${h.matches}`,
    `- ${h.teamA} wins: ${h.teamAWins}`,
    `- ${h.teamB} wins: ${h.teamBWins}`,
    `- Draws: ${h.draws}`,
    `- Goals: ${h.teamA} ${h.teamAGoals} - ${h.teamBGoals} ${h.teamB}`,
  ].join("\n");
}

export function formatStandings(rows: (TeamRecord & { displayName?: string })[]): string {
  if (rows.length === 0) return "No standings (no matches found).";
  return rows
    .map((r, i) => {
      const pos = String(i + 1).padStart(2);
      return `${pos}. ${r.team} - ${r.points} pts (${r.wins}W ${r.draws}D ${r.losses}L, GF ${r.goalsFor} GA ${r.goalsAgainst})`;
    })
    .join("\n");
}

export function formatPlayer(p: Player): string {
  return `${p.name} - Overall: ${p.overall ?? "?"}, Position: ${p.position ?? "?"}, Club: ${p.club || "?"}, Nationality: ${p.nationality}`;
}

export function formatPlayers(players: Player[], limit?: number): string {
  if (players.length === 0) return "No players found.";
  const slice = limit ? players.slice(0, limit) : players;
  return slice.map((p, i) => `${i + 1}. ${formatPlayer(p)}`).join("\n");
}
