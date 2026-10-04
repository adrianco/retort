/**
 * Core domain types: matches, players and the competitions they belong to.
 */
import { fold } from '../text.js';

export const COMPETITIONS = ['Brasileirão', 'Copa do Brasil', 'Libertadores', 'Serie B', 'Serie C'] as const;
export type Competition = (typeof COMPETITIONS)[number];

export const LEAGUES: ReadonlySet<Competition> = new Set(['Brasileirão', 'Serie B', 'Serie C']);
export const DOMESTIC: ReadonlySet<Competition> = new Set(['Brasileirão', 'Copa do Brasil', 'Serie B', 'Serie C']);

/** Interpret the many ways people name a competition. */
export function parseCompetition(text: string): Competition | undefined {
  const t = fold(text).replace(/[^a-z0-9 ]/g, ' ').replace(/\s+/g, ' ').trim();
  if (!t) return undefined;
  if (t.includes('libertadores')) return 'Libertadores';
  if (t.includes('copa do brasil') || t.includes('brazilian cup') || t === 'cup' || t.includes('copa brasil')) return 'Copa do Brasil';
  if (/\bserie b\b/.test(t) || t.includes('serie b')) return 'Serie B';
  if (/\bserie c\b/.test(t)) return 'Serie C';
  if (t.includes('brasileir') || /\bserie a\b/.test(t) || t.includes('campeonato brasileiro') || t === 'league' || t.includes('brazilian league')) {
    return 'Brasileirão';
  }
  return undefined;
}

export interface MatchStats {
  corners?: { home: number; away: number };
  shots?: { home: number; away: number };
  attacks?: { home: number; away: number };
}

export interface Match {
  competition: Competition;
  season: number;
  date: string; // yyyy-mm-dd
  time?: string;
  home: string; // team key
  away: string; // team key
  homeGoals: number;
  awayGoals: number;
  round?: number;
  stage?: string;
  arena?: string;
  stats?: MatchStats;
  sources: string[];
}

export interface Player {
  id: string;
  name: string;
  age?: number;
  nationality: string;
  overall: number;
  potential?: number;
  club: string;
  clubKey?: string;
  position: string;
  jerseyNumber?: number;
  height?: string;
  weight?: string;
  preferredFoot?: string;
  value?: string;
  wage?: string;
  skills: Record<string, number>;
}

export const POSITION_GROUPS: Record<string, string[]> = {
  goalkeeper: ['GK'],
  defender: ['CB', 'LCB', 'RCB', 'LB', 'RB', 'LWB', 'RWB'],
  midfielder: ['CM', 'LCM', 'RCM', 'CDM', 'LDM', 'RDM', 'CAM', 'LAM', 'RAM', 'LM', 'RM'],
  forward: ['ST', 'LS', 'RS', 'CF', 'LF', 'RF', 'LW', 'RW'],
};

/** "forwards", "Forward", "attacker", "striker", "ST" → the FIFA position codes meant. */
export function positionsFor(text: string): string[] {
  const t = fold(text).replace(/s$/, '');
  const synonyms: Record<string, string> = {
    goalkeeper: 'goalkeeper', keeper: 'goalkeeper', goleiro: 'goalkeeper', gk: 'goalkeeper',
    defender: 'defender', defence: 'defender', defense: 'defender', zagueiro: 'defender',
    midfielder: 'midfielder', midfield: 'midfielder', meia: 'midfielder',
    forward: 'forward', attacker: 'forward', striker: 'forward', atacante: 'forward', winger: 'forward',
  };
  const group = synonyms[t];
  if (group) return POSITION_GROUPS[group];
  return [text.trim().toUpperCase()];
}

export function winner(match: Match): string | undefined {
  if (match.homeGoals > match.awayGoals) return match.home;
  if (match.awayGoals > match.homeGoals) return match.away;
  return undefined;
}
