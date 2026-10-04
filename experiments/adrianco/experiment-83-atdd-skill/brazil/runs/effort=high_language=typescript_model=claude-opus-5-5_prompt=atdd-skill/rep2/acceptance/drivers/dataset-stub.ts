/**
 * Stub for the system's external data sources: the Kaggle CSV datasets.
 *
 * A translator, not a simulation. The DSL tells it which matches and players
 * exist; it writes them into a private directory using exactly the file
 * names, columns, team naming conventions and date formats of the real
 * datasets ("Palmeiras-SP", "Atlético - MG", "29/03/2003", "2.0" goals...),
 * so the system meets the same variety it meets in production.
 */
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';

export type LeagueDataset = 'serie-a-dataset' | 'historical-dataset' | 'extended-stats-dataset';

interface Played {
  home: string;
  away: string;
  homeGoals: number;
  awayGoals: number;
  date: string; // ISO yyyy-mm-dd
  season: number;
}

export interface LeagueMatchRecord extends Played {
  dataset: LeagueDataset;
  division: 'Serie A' | 'Serie B' | 'Serie C';
  round: number;
  corners?: [number, number];
  shots?: [number, number];
}

export interface CupMatchRecord extends Played {
  stage?: string;
}

export interface LibertadoresMatchRecord extends Played {
  stage: string;
}

export interface PlayerRecord {
  id: number;
  name: string;
  nationality: string;
  club: string;
  overall: number;
  potential: number;
  position: string;
  age: number;
  jerseyNumber: number;
}

/** How each dataset spells a club, where it differs from the plain rule. */
interface ClubSpelling {
  state: string;
  serieA?: string;
  historical?: string;
  extended?: string;
  cup?: string;
  libertadores?: string;
  fifa?: string;
}

const CLUBS: Record<string, ClubSpelling> = {
  flamengo: { state: 'RJ' },
  fluminense: { state: 'RJ' },
  botafogo: { state: 'RJ', historical: 'Botafogo-RJ', extended: 'Botafogo RJ' },
  'vasco da gama': { state: 'RJ', historical: 'Vasco', extended: 'Vasco Da Gama RJ', libertadores: 'Vasco' },
  corinthians: { state: 'SP' },
  palmeiras: { state: 'SP' },
  santos: { state: 'SP' },
  'sao paulo': { state: 'SP' },
  'red bull bragantino': { state: 'SP', extended: 'Bragantino' },
  gremio: { state: 'RS' },
  internacional: { state: 'RS' },
  juventude: { state: 'RS', extended: 'EC Juventude' },
  cruzeiro: { state: 'MG' },
  'atletico mineiro': { state: 'MG', serieA: 'Atletico-MG', historical: 'Atlético-MG', cup: 'Atlético - MG', libertadores: 'Atlético-MG' },
  'america mineiro': { state: 'MG', serieA: 'America-MG', historical: 'América-MG', extended: 'America MG', cup: 'América - MG', libertadores: 'América-MG', fifa: 'América FC (Minas Gerais)' },
  'athletico paranaense': { state: 'PR', serieA: 'Atletico-PR', historical: 'Athletico-PR', libertadores: 'Athletico', fifa: 'Atlético Paranaense' },
  'atletico goianiense': { state: 'GO', serieA: 'Atletico-GO', historical: 'Atlético-GO', cup: 'Atlético - GO' },
  coritiba: { state: 'PR' },
  parana: { state: 'PR' },
  goias: { state: 'GO' },
  bahia: { state: 'BA', extended: 'EC Bahia' },
  vitoria: { state: 'BA', extended: 'EC Vitoria' },
  sport: { state: 'PE', extended: 'Sport Recife', fifa: 'Sport Club do Recife' },
  nautico: { state: 'PE', extended: 'Nautico Capibaribe' },
  'santa cruz': { state: 'PE' },
  ceara: { state: 'CE', fifa: 'Ceará Sporting Club' },
  fortaleza: { state: 'CE', extended: 'Fortaleza EC' },
  chapecoense: { state: 'SC' },
  avai: { state: 'SC' },
  figueirense: { state: 'SC' },
  criciuma: { state: 'SC' },
  joinville: { state: 'SC' },
  cuiaba: { state: 'MT' },
  csa: { state: 'AL', serieA: 'Csa-AL' },
};

function ascii(text: string): string {
  return text.normalize('NFD').replace(/[̀-ͯ]/g, '');
}

function clubKey(name: string): string {
  return ascii(name).toLowerCase().trim();
}

function spelling(name: string): ClubSpelling {
  return CLUBS[clubKey(name)] ?? { state: 'SP' };
}

const as = {
  serieA: (name: string) => spelling(name).serieA ?? `${ascii(name)}-${spelling(name).state}`,
  historical: (name: string) => spelling(name).historical ?? name,
  extended: (name: string) => spelling(name).extended ?? ascii(name),
  cup: (name: string) => spelling(name).cup ?? `${name} - ${spelling(name).state}`,
  libertadores: (name: string) => spelling(name).libertadores ?? name,
  fifa: (name: string) => spelling(name).fifa ?? name,
};

/** The Copa do Brasil dataset only numbers its rounds; the last rounds are the knockout stages. */
const CUP_ROUND_FOR_STAGE: Record<string, number> = {
  final: 8,
  semifinals: 7,
  quarterfinals: 6,
  'round of 16': 5,
};

function csvField(value: string | number | undefined): string {
  if (value === undefined) return '';
  const text = String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function quoted(value: string | number): string {
  return `"${String(value).replace(/"/g, '""')}"`;
}

function brazilianDate(iso: string): string {
  const [y, m, d] = iso.split('-');
  return `${d}/${m}/${y}`;
}

function winner(m: Played): string {
  if (m.homeGoals > m.awayGoals) return 'Mandante';
  if (m.homeGoals < m.awayGoals) return 'Visitante';
  return 'Empate';
}

function result(goalsFor: number, goalsAgainst: number): string {
  if (goalsFor > goalsAgainst) return 'WON';
  if (goalsFor < goalsAgainst) return 'LOST';
  return 'DRAW';
}

const FIFA_HEADER =
  '﻿,ID,Name,Age,Photo,Nationality,Flag,Overall,Potential,Club,Club Logo,Value,Wage,Special,Preferred Foot,International Reputation,Weak Foot,Skill Moves,Work Rate,Body Type,Real Face,Position,Jersey Number,Joined,Loaned From,Contract Valid Until,Height,Weight,LS,ST,RS,LW,LF,CF,RF,RW,LAM,CAM,RAM,LM,LCM,CM,RCM,RM,LWB,LDM,CDM,RDM,RWB,LB,LCB,CB,RCB,RB,Crossing,Finishing,HeadingAccuracy,ShortPassing,Volleys,Dribbling,Curve,FKAccuracy,LongPassing,BallControl,Acceleration,SprintSpeed,Agility,Reactions,Balance,ShotPower,Jumping,Stamina,Strength,LongShots,Aggression,Interceptions,Positioning,Vision,Penalties,Composure,Marking,StandingTackle,SlidingTackle,GKDiving,GKHandling,GKKicking,GKPositioning,GKReflexes,Release Clause';

export class DatasetStub {
  private readonly league: LeagueMatchRecord[] = [];
  private readonly cup: CupMatchRecord[] = [];
  private readonly libertadores: LibertadoresMatchRecord[] = [];
  private readonly players: PlayerRecord[] = [];

  private constructor(readonly directory: string) {}

  static async create(): Promise<DatasetStub> {
    return new DatasetStub(await mkdtemp(path.join(tmpdir(), 'soccer-datasets-')));
  }

  recordLeagueMatch(match: LeagueMatchRecord): void {
    if (match.dataset !== 'extended-stats-dataset' && match.division !== 'Serie A') {
      throw new Error(`The ${match.dataset} only records Série A matches`);
    }
    this.league.push(match);
  }

  recordCupMatch(match: CupMatchRecord): void {
    this.cup.push(match);
  }

  recordLibertadoresMatch(match: LibertadoresMatchRecord): void {
    this.libertadores.push(match);
  }

  recordPlayer(player: PlayerRecord): void {
    this.players.push(player);
  }

  /** Writes every dataset file that has content. */
  async publish(): Promise<void> {
    const serieA = this.league.filter((m) => m.dataset === 'serie-a-dataset');
    const historical = this.league.filter((m) => m.dataset === 'historical-dataset');
    const extended = this.league.filter((m) => m.dataset === 'extended-stats-dataset');

    if (serieA.length) {
      await this.write('Brasileirao_Matches.csv', [
        '"datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"',
        ...serieA.map((m) =>
          [
            `${m.date} 16:00:00`,
            quoted(as.serieA(m.home)),
            quoted(spelling(m.home).state),
            quoted(as.serieA(m.away)),
            quoted(spelling(m.away).state),
            m.homeGoals,
            m.awayGoals,
            m.season,
            m.round,
          ].join(','),
        ),
      ]);
    }

    if (historical.length) {
      await this.write('novo_campeonato_brasileiro.csv', [
        'ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS',
        ...historical.map((m, i) =>
          [
            `${m.season}.${String(m.round).padStart(2, '0')}.${String(i + 1).padStart(4, '0')}`,
            brazilianDate(m.date),
            m.season,
            m.round,
            csvField(as.historical(m.home)),
            csvField(as.historical(m.away)),
            m.homeGoals,
            m.awayGoals,
            spelling(m.home).state,
            spelling(m.away).state,
            winner(m),
            'Estádio Teste',
            '',
          ].join(','),
        ),
      ]);
    }

    if (extended.length) {
      await this.write('BR-Football-Dataset.csv', [
        'tournament,home,home_goal,away_goal,away,home_corner,away_corner,home_attack,away_attack,home_shots,away_shots,time,date,ht_diff,at_diff,ht_result,at_result,total_corners',
        ...extended.map((m) =>
          [
            m.division,
            csvField(as.extended(m.home)),
            m.homeGoals.toFixed(1),
            m.awayGoals.toFixed(1),
            csvField(as.extended(m.away)),
            m.corners ? m.corners[0].toFixed(1) : '',
            m.corners ? m.corners[1].toFixed(1) : '',
            '',
            '',
            m.shots ? m.shots[0].toFixed(1) : '',
            m.shots ? m.shots[1].toFixed(1) : '',
            '20:00:00',
            m.date,
            (m.homeGoals - m.awayGoals).toFixed(1),
            (m.awayGoals - m.homeGoals).toFixed(1),
            result(m.homeGoals, m.awayGoals),
            result(m.awayGoals, m.homeGoals),
            m.corners ? (m.corners[0] + m.corners[1]).toFixed(1) : '',
          ].join(','),
        ),
      ]);
    }

    if (this.cup.length) {
      await this.write('Brazilian_Cup_Matches.csv', [
        '"round","datetime","home_team","away_team","home_goal","away_goal","season"',
        ...this.cup.map((m) =>
          [
            quoted(m.stage ? this.cupRound(m.stage) : 1),
            `${m.date} 21:30:00`,
            quoted(as.cup(m.home)),
            quoted(as.cup(m.away)),
            m.homeGoals,
            m.awayGoals,
            m.season,
          ].join(','),
        ),
      ]);
    }

    if (this.libertadores.length) {
      await this.write('Libertadores_Matches.csv', [
        '"datetime","home_team","away_team","home_goal","away_goal","season","stage"',
        ...this.libertadores.map((m) =>
          [
            `${m.date} 21:30:00`,
            quoted(as.libertadores(m.home)),
            quoted(as.libertadores(m.away)),
            quoted(m.homeGoals),
            quoted(m.awayGoals),
            m.season,
            quoted(m.stage),
          ].join(','),
        ),
      ]);
    }

    if (this.players.length) {
      const columns = FIFA_HEADER.replace('﻿', '').split(',');
      await this.write('fifa_data.csv', [
        FIFA_HEADER,
        ...this.players.map((p, i) => {
          const values: Record<string, string | number> = {
            '': i,
            ID: p.id,
            Name: p.name,
            Age: p.age,
            Nationality: p.nationality,
            Overall: p.overall,
            Potential: p.potential,
            Club: as.fifa(p.club),
            'Preferred Foot': 'Right',
            Position: p.position,
            'Jersey Number': p.jerseyNumber,
            Height: "5'11",
            Weight: '165lbs',
            Value: '€10M',
            Wage: '€50K',
            Finishing: p.overall,
            Dribbling: p.overall,
            ShortPassing: p.overall,
          };
          return columns.map((c) => csvField(values[c])).join(',');
        }),
      ]);
    }
  }

  async dispose(): Promise<void> {
    await rm(this.directory, { recursive: true, force: true });
  }

  private cupRound(stage: string): number {
    const round = CUP_ROUND_FOR_STAGE[stage];
    if (!round) throw new Error(`The Copa do Brasil dataset has no round for stage "${stage}"`);
    return round;
  }

  private async write(file: string, lines: string[]): Promise<void> {
    await writeFile(path.join(this.directory, file), lines.join('\n') + '\n', 'utf8');
  }
}
