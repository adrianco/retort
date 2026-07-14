import { loadAllData } from '../data/loader.js';
import { normalizeTeamName } from '../data/normalizer.js';

export interface StandingsArgs {
  competition: string;
  season: number;
}

export function getStandings(args: StandingsArgs): any[] {
  const { competition, season } = args;
  const data = loadAllData();

  let matches: any[] = [];

  if (competition === 'brasileirao') {
    matches = data.brasileirao.filter(m => Number(m.season) === season);
  } else if (competition === 'historico') {
    matches = data.historico
      .filter(m => Number(m.Ano) === season)
      .map(m => ({
        home_team: m.Equipe_mandante,
        away_team: m.Equipe_visitante,
        home_goal: m.Gols_mandante,
        away_goal: m.Gols_visitante,
      }));
  } else {
    return [];
  }

  // Use raw team name as key (preserves state suffix to avoid merging Atletico-MG and Atletico-PR)
  // but display the normalized name
  const teamStats: Map<string, { displayName: string; played: number; won: number; drawn: number; lost: number; gf: number; ga: number; points: number }> = new Map();

  const getOrCreate = (team: string) => {
    // Use raw name as key to avoid false merges (e.g. Atletico-MG vs Atletico-PR)
    if (!teamStats.has(team)) {
      teamStats.set(team, { displayName: normalizeTeamName(team), played: 0, won: 0, drawn: 0, lost: 0, gf: 0, ga: 0, points: 0 });
    }
    return teamStats.get(team)!;
  };

  for (const m of matches) {
    const homeGoals = Number(m.home_goal);
    const awayGoals = Number(m.away_goal);

    const homeStats = getOrCreate(m.home_team);
    const awayStats = getOrCreate(m.away_team);

    homeStats.played++;
    awayStats.played++;
    homeStats.gf += homeGoals;
    homeStats.ga += awayGoals;
    awayStats.gf += awayGoals;
    awayStats.ga += homeGoals;

    if (homeGoals > awayGoals) {
      homeStats.won++;
      homeStats.points += 3;
      awayStats.lost++;
    } else if (homeGoals < awayGoals) {
      awayStats.won++;
      awayStats.points += 3;
      homeStats.lost++;
    } else {
      homeStats.drawn++;
      homeStats.points++;
      awayStats.drawn++;
      awayStats.points++;
    }
  }

  const standings = Array.from(teamStats.entries()).map(([_rawTeam, stats]) => ({
    team: stats.displayName,
    played: stats.played,
    won: stats.won,
    drawn: stats.drawn,
    lost: stats.lost,
    gf: stats.gf,
    ga: stats.ga,
    gd: stats.gf - stats.ga,
    points: stats.points,
  }));

  standings.sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    return b.gd - a.gd;
  });

  return standings.map((s, i) => ({ position: i + 1, ...s }));
}
