import { loadAllData } from '../data/loader.js';
import { teamsMatch } from '../data/normalizer.js';

export interface FindMatchesArgs {
  team?: string;
  competition?: string;
  season?: number;
  limit?: number;
}

export function findMatches(args: FindMatchesArgs): any[] {
  const { team, competition, season, limit = 20 } = args;
  const data = loadAllData();

  let results: any[] = [];

  const filterMatches = (matches: any[], homeField: string, awayField: string, seasonField: string) => {
    return matches.filter(m => {
      if (team && !teamsMatch(m[homeField] || '', team) && !teamsMatch(m[awayField] || '', team)) {
        return false;
      }
      if (season !== undefined) {
        const mSeason = Number(m[seasonField]);
        if (mSeason !== season) return false;
      }
      return true;
    });
  };

  if (!competition || competition === 'brasileirao') {
    const filtered = filterMatches(data.brasileirao, 'home_team', 'away_team', 'season');
    results = results.concat(filtered.map(m => ({ ...m, _source: 'brasileirao' })));
  }

  if (!competition || competition === 'copa_do_brasil') {
    const filtered = filterMatches(data.cup, 'home_team', 'away_team', 'season');
    results = results.concat(filtered.map(m => ({ ...m, _source: 'copa_do_brasil' })));
  }

  if (!competition || competition === 'libertadores') {
    const filtered = filterMatches(data.libertadores, 'home_team', 'away_team', 'season');
    results = results.concat(filtered.map(m => ({ ...m, _source: 'libertadores' })));
  }

  if (!competition || competition === 'br_football') {
    const brFiltered = data.brFootball.filter(m => {
      if (team && !teamsMatch(m.home || '', team) && !teamsMatch(m.away || '', team)) return false;
      if (season !== undefined) {
        const d = m.date || '';
        if (!d.includes(String(season))) return false;
      }
      return true;
    });
    results = results.concat(brFiltered.map(m => ({
      home_team: m.home,
      away_team: m.away,
      home_goal: m.home_goal,
      away_goal: m.away_goal,
      season: m.date ? new Date(m.date).getFullYear() : undefined,
      ...m,
      _source: 'br_football'
    })));
  }

  if (!competition || competition === 'historico') {
    const histFiltered = data.historico.filter(m => {
      if (team && !teamsMatch(m.Equipe_mandante || '', team) && !teamsMatch(m.Equipe_visitante || '', team)) return false;
      if (season !== undefined) {
        const mSeason = Number(m.Ano);
        if (mSeason !== season) return false;
      }
      return true;
    });
    results = results.concat(histFiltered.map(m => ({
      home_team: m.Equipe_mandante,
      away_team: m.Equipe_visitante,
      home_goal: m.Gols_mandante,
      away_goal: m.Gols_visitante,
      season: Number(m.Ano),
      round: m.Rodada,
      ...m,
      _source: 'historico'
    })));
  }

  return results.slice(0, limit);
}
