import type { Match } from "./types.js";

export interface StandingsRow {
  team: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  points: number;
}

export function calculateStandings(matches: Match[], competition: string, season: number): StandingsRow[] {
  const relevant = matches.filter(
    (m) => m.competition.toLowerCase() === competition.toLowerCase() && m.season === season,
  );

  const rows = new Map<string, StandingsRow>();
  const getRow = (team: string): StandingsRow => {
    let row = rows.get(team);
    if (!row) {
      row = { team, played: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0, goalDifference: 0, points: 0 };
      rows.set(team, row);
    }
    return row;
  };

  for (const m of relevant) {
    const home = getRow(m.homeTeam);
    const away = getRow(m.awayTeam);

    home.played++;
    away.played++;
    home.goalsFor += m.homeGoals;
    home.goalsAgainst += m.awayGoals;
    away.goalsFor += m.awayGoals;
    away.goalsAgainst += m.homeGoals;

    if (m.homeGoals > m.awayGoals) {
      home.wins++;
      home.points += 3;
      away.losses++;
    } else if (m.homeGoals < m.awayGoals) {
      away.wins++;
      away.points += 3;
      home.losses++;
    } else {
      home.draws++;
      away.draws++;
      home.points += 1;
      away.points += 1;
    }
  }

  for (const row of rows.values()) {
    row.goalDifference = row.goalsFor - row.goalsAgainst;
  }

  return Array.from(rows.values()).sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    if (b.goalDifference !== a.goalDifference) return b.goalDifference - a.goalDifference;
    if (b.goalsFor !== a.goalsFor) return b.goalsFor - a.goalsFor;
    return a.team.localeCompare(b.team);
  });
}
