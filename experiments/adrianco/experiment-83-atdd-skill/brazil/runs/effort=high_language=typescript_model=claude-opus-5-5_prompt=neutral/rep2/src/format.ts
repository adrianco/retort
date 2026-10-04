/**
 * Plain-text formatting of query results for MCP tool responses.
 * Output is compact, human-readable and easy for an LLM to quote.
 */

import { COMPETITION_NAMES, type CompetitionId, type Match, type Player } from "./data.js";
import type { Record_, SoccerKnowledgeBase, StandingRow, Tie } from "./queries.js";

export const pct = (x: number) => `${(x * 100).toFixed(1)}%`;
export const fixed = (x: number, d = 2) => x.toFixed(d);

export function matchContext(m: Match): string {
  const parts: string[] = [COMPETITION_NAMES[m.competition]];
  if (m.round) parts.push(`Round ${m.round}`);
  if (m.stage) parts.push(m.stage.replace(/\b\w/g, (c) => c.toUpperCase()));
  if (!m.round && !m.stage) parts.push(`${m.season}`);
  return parts.join(" ");
}

export function formatMatch(kb: SoccerKnowledgeBase, m: Match, opts: { stats?: boolean } = {}): string {
  const date = m.date ?? `${m.season} (date unknown)`;
  let line = `${date}: ${kb.teamName(m.home)} ${m.homeGoals}-${m.awayGoals} ${kb.teamName(m.away)} (${matchContext(m)})`;
  if (m.stadium) line += ` @ ${m.stadium}`;
  if (opts.stats && m.stats && m.stats.homeShots !== undefined) {
    const s = m.stats;
    line += ` [shots ${s.homeShots}-${s.awayShots}, corners ${s.homeCorners}-${s.awayCorners}, attacks ${s.homeAttacks}-${s.awayAttacks}]`;
  }
  return line;
}

export function formatMatchList(kb: SoccerKnowledgeBase, matches: Match[], limit: number, opts: { stats?: boolean } = {}): string[] {
  const lines = matches.slice(0, limit).map((m) => `- ${formatMatch(kb, m, opts)}`);
  if (matches.length > limit) lines.push(`- ... (${matches.length - limit} more matches in dataset)`);
  return lines;
}

export function formatRecord(r: Record_, indent = "- "): string[] {
  const wr = r.matches ? pct(r.wins / r.matches) : "n/a";
  return [
    `${indent}Matches: ${r.matches}`,
    `${indent}Wins: ${r.wins}, Draws: ${r.draws}, Losses: ${r.losses}`,
    `${indent}Goals For: ${r.goalsFor}, Goals Against: ${r.goalsAgainst} (GD ${signed(r.goalsFor - r.goalsAgainst)})`,
    `${indent}Points: ${r.points} (${r.matches ? fixed(r.points / r.matches) : "0"} per game)`,
    `${indent}Win rate: ${wr}`,
  ];
}

export const signed = (n: number) => (n > 0 ? `+${n}` : `${n}`);

export function recordLine(r: Record_): string {
  return `${r.matches} played, ${r.wins}W ${r.draws}D ${r.losses}L, GF ${r.goalsFor} GA ${r.goalsAgainst}, win rate ${r.matches ? pct(r.wins / r.matches) : "n/a"}`;
}

export function standingLine(r: StandingRow): string {
  const note = r.note ? ` - ${r.note}` : "";
  return `${r.position}. ${r.name} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L) GF ${r.goalsFor} GA ${r.goalsAgainst} GD ${signed(r.goalDiff)}${note}`;
}

export function tieLine(kb: SoccerKnowledgeBase, t: Tie): string {
  const legs = t.legs.map((m) => `${m.date ?? "?"} ${kb.teamName(m.home)} ${m.homeGoals}-${m.awayGoals} ${kb.teamName(m.away)}`).join("; ");
  const outcome = t.winner ? `${kb.teamName(t.winner)} advance` : t.note;
  const agg = t.legs.length > 1 ? `aggregate ${t.nameA} ${t.aggregateA}-${t.aggregateB} ${t.nameB}` : `${t.nameA} ${t.aggregateA}-${t.aggregateB} ${t.nameB}`;
  return `${agg} -> ${outcome} [${legs}]`;
}

export function playerLine(p: Player, i?: number): string {
  const prefix = i !== undefined ? `${i + 1}. ` : "- ";
  return `${prefix}${p.name} - Overall: ${p.overall ?? "?"}, Potential: ${p.potential ?? "?"}, Position: ${p.position || "?"}, Age: ${p.age ?? "?"}, Nationality: ${p.nationality}, Club: ${p.club || "(none)"}`;
}

export function playerDetail(p: Player): string {
  const top = Object.entries(p.skills)
    .filter(([k]) => !k.startsWith("GK") || p.position === "GK")
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([k, v]) => `${k} ${v}`)
    .join(", ");
  return [
    `${p.name} (FIFA ID ${p.id})`,
    `- Age: ${p.age ?? "?"}, Nationality: ${p.nationality}`,
    `- Club: ${p.club || "(none)"}${p.loanedFrom ? ` (on loan from ${p.loanedFrom})` : ""}${p.jerseyNumber !== undefined ? `, Jersey #${p.jerseyNumber}` : ""}`,
    `- Position: ${p.position || "?"}, Preferred foot: ${p.preferredFoot ?? "?"}`,
    `- Overall: ${p.overall ?? "?"}, Potential: ${p.potential ?? "?"}`,
    `- Height: ${p.height ?? "?"}, Weight: ${p.weight ?? "?"}`,
    `- Value: ${p.value ?? "?"}, Wage: ${p.wage ?? "?"}${p.contractValidUntil ? `, Contract until: ${p.contractValidUntil}` : ""}`,
    `- Top attributes: ${top || "n/a"}`,
  ].join("\n");
}

export const competitionName = (c: CompetitionId) => COMPETITION_NAMES[c];
