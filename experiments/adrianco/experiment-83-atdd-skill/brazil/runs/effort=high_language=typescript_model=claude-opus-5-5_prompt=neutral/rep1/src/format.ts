/**
 * Text formatting for query results. Output follows the answer formats in
 * the specification, e.g.
 *   - 2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A Round 22)
 */
import { COMPETITIONS, type Match, type Player } from "./data.js";
import { pct } from "./normalize.js";
import type { SoccerQueries, StandingRow, Tie, TeamRecord } from "./query.js";

export function matchContext(m: Match): string {
  const parts: string[] = [COMPETITIONS[m.competition]];
  if (m.competition === "libertadores" || m.competition === "copa-do-brasil") {
    if (m.stage) parts.push(m.stage === "final" ? "Final" : m.stage.replace(/^round (\d+)$/, "Round $1"));
    else parts.push(String(m.season));
  } else if (m.round !== undefined) parts.push(`${m.season} Round ${m.round}`);
  else parts.push(String(m.season));
  return parts.join(" ");
}

export function formatMatch(q: SoccerQueries, m: Match, opts: { stats?: boolean } = {}): string {
  let s = `${m.date}: ${q.teamName(m.homeId)} ${m.homeGoals}-${m.awayGoals} ${q.teamName(m.awayId)} (${matchContext(m)})`;
  if (m.arena) s += ` @ ${m.arena}`;
  if (opts.stats && m.stats) {
    const st = m.stats;
    const bits: string[] = [];
    if (st.homeShots != null && st.awayShots != null) bits.push(`shots ${st.homeShots}-${st.awayShots}`);
    if (st.homeCorners != null && st.awayCorners != null) bits.push(`corners ${st.homeCorners}-${st.awayCorners}`);
    if (st.homeAttacks != null && st.awayAttacks != null) bits.push(`attacks ${st.homeAttacks}-${st.awayAttacks}`);
    if (bits.length) s += ` [${bits.join(", ")}]`;
  }
  return s;
}

export function formatRecord(rec: TeamRecord): string[] {
  return [
    `- Matches: ${rec.played}`,
    `- Wins: ${rec.wins}, Draws: ${rec.draws}, Losses: ${rec.losses}`,
    `- Goals For: ${rec.goalsFor}, Goals Against: ${rec.goalsAgainst} (GD ${signed(rec.goalsFor - rec.goalsAgainst)})`,
    `- Points: ${rec.points} (${rec.played ? (rec.points / rec.played).toFixed(2) : "0.00"} per game)`,
    `- Win rate: ${pct(rec.wins, rec.played)}`,
  ];
}

export function shortRecord(rec: TeamRecord): string {
  return `${rec.played} played, ${rec.wins}W ${rec.draws}D ${rec.losses}L, goals ${rec.goalsFor}-${rec.goalsAgainst}, win rate ${pct(rec.wins, rec.played)}`;
}

const signed = (n: number) => (n > 0 ? `+${n}` : String(n));

export function formatStandingRow(r: StandingRow): string {
  return `${r.position}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L) GF ${r.goalsFor} GA ${r.goalsAgainst} GD ${signed(r.goalDifference)}`;
}

export function formatTie(q: SoccerQueries, t: Tie): string {
  const legs = t.legs.map((l) => `${l.date} ${q.teamName(l.homeId)} ${l.homeGoals}-${l.awayGoals} ${q.teamName(l.awayId)}`).join("; ");
  let winner = "";
  if (t.winnerId) {
    const level = t.aggregateA === t.aggregateB;
    const how = t.legs.length > 1 ? "level on aggregate; away goals/penalties" : "drawn; penalties";
    winner = ` -> ${q.teamName(t.winnerId)} ${t.stage === "final" ? "won" : "advanced"}${level ? ` (${how})` : ""}`;
  } else if (t.aggregateA === t.aggregateB) {
    winner = ` -> ${t.legs.length > 1 ? "level on aggregate" : "drawn"} (decided on penalties; winner not in data)`;
  }
  const agg = t.legs.length > 1 ? ` (agg ${t.aggregateA}-${t.aggregateB})` : "";
  return `${t.teamA} vs ${t.teamB}${agg}${winner}\n    ${legs}`;
}

export function formatPlayerLine(p: Player, i?: number): string {
  const prefix = i !== undefined ? `${i + 1}. ` : "- ";
  return `${prefix}${p.name} - Overall: ${p.overall ?? "?"}, Potential: ${p.potential ?? "?"}, Position: ${p.position || "?"}, Age: ${p.age ?? "?"}, Nationality: ${p.nationality}, Club: ${p.club || "(free agent)"}`;
}

export function formatPlayerDetail(p: Player, q: SoccerQueries): string {
  const lines = [
    `${p.name} (FIFA ID ${p.id})`,
    `- Club: ${p.club || "(free agent)"}${p.teamId ? ` [matches as ${q.teamName(p.teamId)} in match data]` : ""}`,
    `- Nationality: ${p.nationality}`,
    `- Age: ${p.age ?? "?"}`,
    `- Position: ${p.position || "?"}${p.jerseyNumber !== null ? `, Jersey #${p.jerseyNumber}` : ""}`,
    `- Overall: ${p.overall ?? "?"}, Potential: ${p.potential ?? "?"}`,
    `- Height: ${p.height || "?"}, Weight: ${p.weight || "?"}, Preferred foot: ${p.preferredFoot || "?"}`,
    `- Value: ${p.value || "?"}, Wage: ${p.wage || "?"}`,
  ];
  const key = ["Finishing", "Dribbling", "ShortPassing", "BallControl", "Acceleration", "SprintSpeed", "Crossing", "HeadingAccuracy", "StandingTackle", "Stamina", "Strength", "Vision"];
  const gk = ["GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes"];
  const shown = (p.position === "GK" ? gk : key).filter((k) => p.skills[k] !== undefined);
  if (shown.length) lines.push(`- Key attributes: ${shown.map((k) => `${k} ${p.skills[k]}`).join(", ")}`);
  return lines.join("\n");
}
