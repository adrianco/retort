/**
 * Readable shorthand used by the specs, e.g.
 *   '2023-09-03 Flamengo 2-1 Fluminense'
 *   '1. Flamengo - 90 pts (28W, 6D, 4L)'
 *   '2020: Palmeiras beat Grêmio 3-0 on aggregate'
 * parsed into the structured values the protocol drivers work with.
 */
import type { ExpectedMatch, ExpectedStandingsRow, ExpectedTie } from '../drivers/soccer-driver.js';

export function parseScore(score: string): [number, number] {
  const m = /^\s*(\d+)\s*-\s*(\d+)\s*$/.exec(score);
  if (!m) throw new Error(`Cannot read score "${score}" — expected e.g. "2-1"`);
  return [Number(m[1]), Number(m[2])];
}

export function parseMatch(line: string): ExpectedMatch {
  const m = /^(\d{4}-\d{2}-\d{2}):? (.+?) (\d+)-(\d+) (.+)$/.exec(line.trim());
  if (!m) throw new Error(`Cannot read match "${line}" — expected e.g. "2023-09-03 Flamengo 2-1 Fluminense"`);
  return { date: m[1], home: m[2], homeGoals: Number(m[3]), awayGoals: Number(m[4]), away: m[5] };
}

export function parseStandingsRow(line: string): ExpectedStandingsRow {
  const m = /^(\d+)\.\s+(.+?)\s+-\s+(\d+) pts \((\d+)W, (\d+)D, (\d+)L\)$/.exec(line.trim());
  if (!m) throw new Error(`Cannot read standings row "${line}" — expected e.g. "1. Flamengo - 90 pts (28W, 6D, 4L)"`);
  return { position: Number(m[1]), team: m[2], points: Number(m[3]), won: Number(m[4]), drawn: Number(m[5]), lost: Number(m[6]) };
}

export function parseTie(line: string): ExpectedTie {
  const m = /^(?:(\d{4}): )?(.+?) beat (.+?) (\d+)-(\d+) on aggregate$/.exec(line.trim());
  if (!m) throw new Error(`Cannot read tie "${line}" — expected e.g. "2020: Palmeiras beat Grêmio 3-0 on aggregate"`);
  return {
    season: m[1] ? Number(m[1]) : undefined,
    winner: m[2],
    loser: m[3],
    winnerGoals: Number(m[4]),
    loserGoals: Number(m[5]),
  };
}
