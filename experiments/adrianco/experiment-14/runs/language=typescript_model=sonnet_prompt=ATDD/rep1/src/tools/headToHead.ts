import { loadAllData } from '../data/loader.js';
import { teamsMatch } from '../data/normalizer.js';

export interface HeadToHeadArgs {
  team1: string;
  team2: string;
  competition?: string;
  season?: number;
}

export function getHeadToHead(args: HeadToHeadArgs): any {
  const { team1, team2, competition, season } = args;
  const data = loadAllData();

  const allMatches: any[] = [
    ...data.brasileirao.map(m => ({ ...m, _source: 'brasileirao' })),
    ...data.cup.map(m => ({ ...m, _source: 'copa_do_brasil' })),
    ...data.libertadores.map(m => ({ ...m, _source: 'libertadores' })),
    ...data.historico.map(m => ({
      home_team: m.Equipe_mandante,
      away_team: m.Equipe_visitante,
      home_goal: m.Gols_mandante,
      away_goal: m.Gols_visitante,
      season: m.Ano,
      ...m,
      _source: 'historico'
    })),
  ];

  const h2hMatches = allMatches.filter(m => {
    const homeIsT1 = teamsMatch(m.home_team || '', team1);
    const homeIsT2 = teamsMatch(m.home_team || '', team2);
    const awayIsT1 = teamsMatch(m.away_team || '', team1);
    const awayIsT2 = teamsMatch(m.away_team || '', team2);

    const isH2H = (homeIsT1 && awayIsT2) || (homeIsT2 && awayIsT1);
    if (!isH2H) return false;

    if (competition && m._source !== competition) return false;
    if (season !== undefined && Number(m.season) !== season) return false;

    return true;
  });

  let team1_wins = 0, team2_wins = 0, draws = 0;

  for (const m of h2hMatches) {
    const hg = Number(m.home_goal);
    const ag = Number(m.away_goal);
    const homeIsT1 = teamsMatch(m.home_team || '', team1);

    if (hg === ag) {
      draws++;
    } else if (hg > ag) {
      if (homeIsT1) team1_wins++; else team2_wins++;
    } else {
      if (homeIsT1) team2_wins++; else team1_wins++;
    }
  }

  return {
    team1,
    team2,
    total_matches: h2hMatches.length,
    team1_wins,
    team2_wins,
    draws,
    matches: h2hMatches.slice(0, 20),
  };
}
