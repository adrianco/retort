export interface BrasileiraoMatch {
  datetime: string;
  homeTeam: string;
  homeTeamState: string;
  awayTeam: string;
  awayTeamState: string;
  homeGoal: number;
  awayGoal: number;
  season: number;
  round: number;
  competition: "Brasileirão";
}

export interface CupMatch {
  round: string;
  datetime: string;
  homeTeam: string;
  awayTeam: string;
  homeGoal: number;
  awayGoal: number;
  season: number;
  competition: "Copa do Brasil";
}

export interface LibertadoresMatch {
  datetime: string;
  homeTeam: string;
  awayTeam: string;
  homeGoal: number;
  awayGoal: number;
  season: number;
  stage: string;
  competition: "Copa Libertadores";
}

export interface ExtendedMatch {
  tournament: string;
  home: string;
  away: string;
  homeGoal: number;
  awayGoal: number;
  homeCorner: number;
  awayCorner: number;
  homeAttack: number;
  awayAttack: number;
  homeShots: number;
  awayShots: number;
  time: string;
  date: string;
  htResult: string;
  atResult: string;
  totalCorners: number;
  competition: string;
}

export interface HistoricalMatch {
  id: string;
  date: string;
  year: number;
  round: number;
  homeTeam: string;
  awayTeam: string;
  homeGoal: number;
  awayGoal: number;
  homeState: string;
  awayState: string;
  winner: string;
  arena: string;
  competition: "Brasileirão";
}

export interface FifaPlayer {
  id: number;
  name: string;
  age: number;
  nationality: string;
  overall: number;
  potential: number;
  club: string;
  position: string;
  jerseyNumber: number;
  height: string;
  weight: string;
  crossing: number;
  finishing: number;
  headingAccuracy: number;
  shortPassing: number;
  dribbling: number;
  curve: number;
  fkAccuracy: number;
  longPassing: number;
  ballControl: number;
  acceleration: number;
  sprintSpeed: number;
  agility: number;
  reactions: number;
  balance: number;
  shotPower: number;
  jumping: number;
  stamina: number;
  strength: number;
  longShots: number;
  aggression: number;
  interceptions: number;
  positioning: number;
  vision: number;
  penalties: number;
  composure: number;
  marking: number;
  standingTackle: number;
  slidingTackle: number;
  preferredFoot: string;
  workRate: string;
  value: string;
  wage: string;
}

export interface UnifiedMatch {
  datetime: string;
  homeTeam: string;
  awayTeam: string;
  homeGoal: number;
  awayGoal: number;
  season: number;
  competition: string;
  round?: string | number;
  stage?: string;
  homeTeamState?: string;
  awayTeamState?: string;
  arena?: string;
  homeCorner?: number;
  awayCorner?: number;
  homeShots?: number;
  awayShots?: number;
}

export interface TeamStats {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  points: number;
  winRate: number;
}

export interface HeadToHead {
  team1: string;
  team2: string;
  team1Wins: number;
  team2Wins: number;
  draws: number;
  totalMatches: number;
  team1Goals: number;
  team2Goals: number;
  matches: UnifiedMatch[];
}
