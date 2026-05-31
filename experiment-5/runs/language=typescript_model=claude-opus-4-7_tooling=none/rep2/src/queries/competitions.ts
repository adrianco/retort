import type { Competition, Dataset } from "../types.js";
import { computeStandings, type StandingsRow } from "./teams.js";

export interface SeasonSummary {
  season: number;
  competition: string;
  champion: StandingsRow | null;
  topThree: StandingsRow[];
  bottomThree: StandingsRow[];
  totalTeams: number;
}

export function seasonSummary(
  dataset: Dataset,
  season: number,
  competition: Competition | string = "Brasileirao",
): SeasonSummary {
  const standings = computeStandings(dataset, { season, competition });
  return {
    season,
    competition: String(competition),
    champion: standings[0] ?? null,
    topThree: standings.slice(0, 3),
    bottomThree: standings.slice(-3).reverse(),
    totalTeams: standings.length,
  };
}

export function listSeasons(dataset: Dataset, competition?: Competition | string): number[] {
  const set = new Set<number>();
  for (const m of dataset.matches) {
    if (competition) {
      const c = String(competition).toLowerCase();
      if (m.competition.toLowerCase() !== c && !m.competitionLabel.toLowerCase().includes(c)) continue;
    }
    if (m.season !== null) set.add(m.season);
  }
  return [...set].sort((a, b) => a - b);
}

export function listCompetitions(dataset: Dataset): { competition: Competition; label: string; matches: number; seasons: number[] }[] {
  const map = new Map<Competition, { label: string; matches: number; seasons: Set<number> }>();
  for (const m of dataset.matches) {
    if (!map.has(m.competition)) map.set(m.competition, { label: m.competitionLabel, matches: 0, seasons: new Set() });
    const v = map.get(m.competition)!;
    v.matches++;
    if (m.season !== null) v.seasons.add(m.season);
  }
  return [...map.entries()].map(([competition, v]) => ({
    competition,
    label: v.label,
    matches: v.matches,
    seasons: [...v.seasons].sort((a, b) => a - b),
  }));
}
