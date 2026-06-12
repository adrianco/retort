import { loadAllData } from '../data/loader.js';
import { teamsMatch } from '../data/normalizer.js';

export interface TeamStatsArgs {
  team: string;
  competition?: string;
  season?: number;
}

export function getTeamStats(args: TeamStatsArgs): any {
  const { team, competition, season } = args;
  const data = loadAllData();

  let matches: Array<{ home_team: string; away_team: string; home_goal: number; away_goal: number; season: number }> = [];

  if (!competition || competition === 'brasileirao') {
    data.brasileirao.forEach(m => {
      if (season !== undefined && Number(m.season) !== season) return;
      matches.push({ home_team: m.home_team, away_team: m.away_team, home_goal: Number(m.home_goal), away_goal: Number(m.away_goal), season: Number(m.season) });
    });
  }

  if (!competition || competition === 'copa_do_brasil') {
    data.cup.forEach(m => {
      if (season !== undefined && Number(m.season) !== season) return;
      matches.push({ home_team: m.home_team, away_team: m.away_team, home_goal: Number(m.home_goal), away_goal: Number(m.away_goal), season: Number(m.season) });
    });
  }

  if (!competition || competition === 'libertadores') {
    data.libertadores.forEach(m => {
      if (season !== undefined && Number(m.season) !== season) return;
      matches.push({ home_team: m.home_team, away_team: m.away_team, home_goal: Number(m.home_goal), away_goal: Number(m.away_goal), season: Number(m.season) });
    });
  }

  let wins = 0, losses = 0, draws = 0, goals_scored = 0, goals_conceded = 0;

  for (const m of matches) {
    const isHome = teamsMatch(m.home_team, team);
    const isAway = teamsMatch(m.away_team, team);
    if (!isHome && !isAway) continue;

    const scored = isHome ? m.home_goal : m.away_goal;
    const conceded = isHome ? m.away_goal : m.home_goal;

    goals_scored += scored;
    goals_conceded += conceded;

    if (scored > conceded) wins++;
    else if (scored < conceded) losses++;
    else draws++;
  }

  const played = wins + losses + draws;
  const points = wins * 3 + draws;

  return {
    team,
    competition: competition || 'all',
    season: season || 'all',
    matches_played: played,
    wins,
    losses,
    draws,
    goals_scored,
    goals_conceded,
    points,
  };
}
