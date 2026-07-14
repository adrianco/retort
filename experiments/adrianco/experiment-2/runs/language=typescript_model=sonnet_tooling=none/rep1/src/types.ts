export interface BrasileiraoMatch {
  datetime: string;
  home_team: string;
  home_team_state: string;
  away_team: string;
  away_team_state: string;
  home_goal: number;
  away_goal: number;
  season: number;
  round: number;
  competition: 'Brasileirao';
}

export interface CupMatch {
  round: string;
  datetime: string;
  home_team: string;
  away_team: string;
  home_goal: number;
  away_goal: number;
  season: number;
  competition: 'Copa do Brasil';
}

export interface LibertadoresMatch {
  datetime: string;
  home_team: string;
  away_team: string;
  home_goal: number;
  away_goal: number;
  season: number;
  stage: string;
  competition: 'Libertadores';
}

export interface BRFootballMatch {
  tournament: string;
  home: string;
  away: string;
  home_goal: number;
  away_goal: number;
  home_corner: number;
  away_corner: number;
  home_attack: number;
  away_attack: number;
  home_shots: number;
  away_shots: number;
  time: string;
  date: string;
  ht_result: string;
  at_result: string;
  total_corners: number;
}

export interface HistoricalMatch {
  ID: string;
  Data: string;
  Ano: number;
  Rodada: number;
  Equipe_mandante: string;
  Equipe_visitante: string;
  Gols_mandante: number;
  Gols_visitante: number;
  Mandante_UF: string;
  Visitante_UF: string;
  Vencedor: string;
  Arena: string;
}

export interface FifaPlayer {
  ID: number;
  Name: string;
  Age: number;
  Nationality: string;
  Overall: number;
  Potential: number;
  Club: string;
  Position: string;
  JerseyNumber: number;
  Height: string;
  Weight: string;
  Value: string;
  Wage: string;
}

export interface NormalizedMatch {
  date: string;
  home_team: string;
  away_team: string;
  home_goal: number;
  away_goal: number;
  season: number;
  competition: string;
  round?: string | number;
  stage?: string;
  arena?: string;
}

export interface TeamStats {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goals_for: number;
  goals_against: number;
  points: number;
}
