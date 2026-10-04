/**
 * Writes the synthetic world described by a spec into a data directory using
 * exactly the file names and formats of the provided Kaggle datasets — the
 * system's natural input interface. Each spec gets its own directory.
 */
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import type { MatchRecord, PlayerRecord } from '../soccer-driver.js';

const SKILL_COLUMNS = [
  'Crossing', 'Finishing', 'HeadingAccuracy', 'ShortPassing', 'Volleys', 'Dribbling', 'Curve', 'FKAccuracy',
  'LongPassing', 'BallControl', 'Acceleration', 'SprintSpeed', 'Agility', 'Reactions', 'Balance', 'ShotPower',
  'Jumping', 'Stamina', 'Strength', 'LongShots', 'Aggression', 'Interceptions', 'Positioning', 'Vision',
  'Penalties', 'Composure', 'Marking', 'StandingTackle', 'SlidingTackle', 'GKDiving', 'GKHandling', 'GKKicking',
  'GKPositioning', 'GKReflexes',
];

function cell(value: unknown, quote = false): string {
  const text = value === undefined || value === null ? '' : String(value);
  return quote || /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function row(values: unknown[], quoted: boolean[] = []): string {
  return values.map((v, i) => cell(v, quoted[i])).join(',');
}

function stateOf(team: string): string {
  return /-([A-Z]{2})$/.exec(team)?.[1] ?? '';
}

function brazilianDate(iso: string): string {
  const [y, m, d] = iso.split('-');
  return `${d}/${m}/${y}`;
}

function outcome(goals: number, conceded: number): string {
  return goals > conceded ? 'WON' : goals < conceded ? 'LOST' : 'DRAW';
}

/** camelCase skill name used by specs → FIFA column name, e.g. sprintSpeed → SprintSpeed, fkAccuracy → FKAccuracy */
function skillColumn(skill: string): string {
  return SKILL_COLUMNS.find((c) => c.toLowerCase() === skill.toLowerCase()) ?? skill;
}

export function writeDatasets(matches: MatchRecord[], players: PlayerRecord[]): string {
  const dir = mkdtempSync(join(tmpdir(), 'brazilian-soccer-spec-'));
  const lines: Record<string, string[]> = {
    'Brasileirao_Matches.csv': ['"datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"'],
    'Brazilian_Cup_Matches.csv': ['"round","datetime","home_team","away_team","home_goal","away_goal","season"'],
    'Libertadores_Matches.csv': ['"datetime","home_team","away_team","home_goal","away_goal","season","stage"'],
    'BR-Football-Dataset.csv': [
      'tournament,home,home_goal,away_goal,away,home_corner,away_corner,home_attack,away_attack,home_shots,away_shots,time,date,ht_diff,at_diff,ht_result,at_result,total_corners',
    ],
    'novo_campeonato_brasileiro.csv': [
      'ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS',
    ],
    'fifa_data.csv': [
      `﻿${row(['', 'ID', 'Name', 'Age', 'Nationality', 'Overall', 'Potential', 'Club', 'Value', 'Wage', 'Preferred Foot', 'Position', 'Jersey Number', 'Height', 'Weight', ...SKILL_COLUMNS])}`,
    ],
  };

  matches.forEach((m, i) => {
    const datetime = `${m.date} 16:00:00`;
    switch (m.dataset) {
      case 'brasileirao':
        lines['Brasileirao_Matches.csv'].push(
          row([datetime, m.home, stateOf(m.home), m.away, stateOf(m.away), m.homeGoals, m.awayGoals, m.season, m.round], [false, true, true, true, true]),
        );
        break;
      case 'cup':
        lines['Brazilian_Cup_Matches.csv'].push(
          row([m.round, datetime, m.home, m.away, m.homeGoals, m.awayGoals, m.season], [true, false, true, true]),
        );
        break;
      case 'libertadores':
        lines['Libertadores_Matches.csv'].push(
          row([datetime, m.home, m.away, m.homeGoals, m.awayGoals, m.season, m.stage], [false, true, true, true, true, false, true]),
        );
        break;
      case 'extended': {
        const tournament = m.competition === 'Brasileirão' ? 'Serie A' : m.competition;
        const [hc, ac] = m.corners ?? [undefined, undefined];
        const [hs, as] = m.shots ?? [undefined, undefined];
        const f = (n: number | undefined) => (n === undefined ? '' : n.toFixed(1));
        lines['BR-Football-Dataset.csv'].push(
          row([
            tournament, m.home, f(m.homeGoals), f(m.awayGoals), m.away, f(hc), f(ac), '', '', f(hs), f(as), '16:00:00', m.date,
            f(m.homeGoals - m.awayGoals), f(m.awayGoals - m.homeGoals), outcome(m.homeGoals, m.awayGoals), outcome(m.awayGoals, m.homeGoals),
            hc === undefined || ac === undefined ? '' : f(hc + ac),
          ]),
        );
        break;
      }
      case 'historical': {
        const winner = m.homeGoals > m.awayGoals ? 'Mandante' : m.homeGoals < m.awayGoals ? 'Visitante' : 'Empate';
        lines['novo_campeonato_brasileiro.csv'].push(
          row([
            `${m.season}.${String(m.round).padStart(2, '0')}.${String(i + 1).padStart(4, '0')}`, brazilianDate(m.date), m.season, m.round,
            m.home, m.away, m.homeGoals, m.awayGoals, stateOf(m.home), stateOf(m.away), winner, 'Estádio', '',
          ]),
        );
        break;
      }
    }
  });

  players.forEach((p, i) => {
    lines['fifa_data.csv'].push(
      row([
        i, 100000 + i, p.name, p.age, p.nationality, p.overall, p.potential, p.club, '€1M', '€10K', 'Right', p.position, p.jerseyNumber,
        "5'11", '170lbs', ...SKILL_COLUMNS.map((c) => {
          const given = Object.entries(p.skills).find(([skill]) => skillColumn(skill) === c);
          return given ? given[1] : 50;
        }),
      ]),
    );
  });

  for (const [file, content] of Object.entries(lines)) {
    writeFileSync(join(dir, file), content.join('\n') + '\n', 'utf8');
  }
  return dir;
}
