import { createReadStream } from 'fs';
import path from 'path';
import { parse } from 'csv-parse';
import type {
  BrasileiraoMatch,
  CupMatch,
  LibertadoresMatch,
  ExtendedMatch,
  HistoricalMatch,
  FifaPlayer,
  NormalizedMatch,
} from './types.js';
import { normalizeTeamName, parseDate, formatDate } from './normalizer.js';

async function parseCsv<T>(
  filePath: string,
  transform: (row: Record<string, string>) => T | null,
): Promise<T[]> {
  return new Promise((resolve, reject) => {
    const results: T[] = [];
    const stream = createReadStream(filePath, { encoding: 'utf8' });
    const parser = parse({
      columns: true,
      skip_empty_lines: true,
      trim: true,
      bom: true,
      relax_column_count: true,
    });

    parser.on('readable', () => {
      let record;
      while ((record = parser.read()) !== null) {
        const row = transform(record);
        if (row !== null) results.push(row);
      }
    });
    parser.on('error', reject);
    parser.on('end', () => resolve(results));
    stream.on('error', reject);
    stream.pipe(parser);
  });
}

function toInt(v: string | undefined): number {
  if (!v) return 0;
  const n = parseInt(v.trim(), 10);
  return isNaN(n) ? 0 : n;
}

function toFloat(v: string | undefined): number {
  if (!v) return 0;
  const n = parseFloat(v.trim());
  return isNaN(n) ? 0 : n;
}

export class DataLoader {
  private dataDir: string;
  private brasileiraoMatches: BrasileiraoMatch[] = [];
  private cupMatches: CupMatch[] = [];
  private libertadoresMatches: LibertadoresMatch[] = [];
  private extendedMatches: ExtendedMatch[] = [];
  private historicalMatches: HistoricalMatch[] = [];
  private fifaPlayers: FifaPlayer[] = [];
  private allNormalized: NormalizedMatch[] = [];
  private loaded = false;

  constructor(dataDir: string) {
    this.dataDir = dataDir;
  }

  async load(): Promise<void> {
    if (this.loaded) return;

    const [brasileirao, cup, libertadores, extended, historical, players] =
      await Promise.all([
        this.loadBrasileiraoMatches(),
        this.loadCupMatches(),
        this.loadLibertadoresMatches(),
        this.loadExtendedMatches(),
        this.loadHistoricalMatches(),
        this.loadFifaPlayers(),
      ]);

    this.brasileiraoMatches = brasileirao;
    this.cupMatches = cup;
    this.libertadoresMatches = libertadores;
    this.extendedMatches = extended;
    this.historicalMatches = historical;
    this.fifaPlayers = players;
    this.allNormalized = this.buildNormalized();
    this.loaded = true;
  }

  private loadBrasileiraoMatches(): Promise<BrasileiraoMatch[]> {
    return parseCsv(
      path.join(this.dataDir, 'Brasileirao_Matches.csv'),
      (row) => ({
        datetime: row['datetime'] ?? '',
        home_team: row['home_team'] ?? '',
        home_team_state: row['home_team_state'] ?? '',
        away_team: row['away_team'] ?? '',
        away_team_state: row['away_team_state'] ?? '',
        home_goal: toInt(row['home_goal']),
        away_goal: toInt(row['away_goal']),
        season: toInt(row['season']),
        round: toInt(row['round']),
      }),
    );
  }

  private loadCupMatches(): Promise<CupMatch[]> {
    return parseCsv(
      path.join(this.dataDir, 'Brazilian_Cup_Matches.csv'),
      (row) => ({
        round: row['round'] ?? '',
        datetime: row['datetime'] ?? '',
        home_team: row['home_team'] ?? '',
        away_team: row['away_team'] ?? '',
        home_goal: toInt(row['home_goal']),
        away_goal: toInt(row['away_goal']),
        season: toInt(row['season']),
      }),
    );
  }

  private loadLibertadoresMatches(): Promise<LibertadoresMatch[]> {
    return parseCsv(
      path.join(this.dataDir, 'Libertadores_Matches.csv'),
      (row) => ({
        datetime: row['datetime'] ?? '',
        home_team: row['home_team'] ?? '',
        away_team: row['away_team'] ?? '',
        home_goal: toInt(row['home_goal']),
        away_goal: toInt(row['away_goal']),
        season: toInt(row['season']),
        stage: row['stage'] ?? '',
      }),
    );
  }

  private loadExtendedMatches(): Promise<ExtendedMatch[]> {
    return parseCsv(
      path.join(this.dataDir, 'BR-Football-Dataset.csv'),
      (row) => ({
        tournament: row['tournament'] ?? '',
        home: row['home'] ?? '',
        away: row['away'] ?? '',
        home_goal: toFloat(row['home_goal']),
        away_goal: toFloat(row['away_goal']),
        home_corner: toFloat(row['home_corner']),
        away_corner: toFloat(row['away_corner']),
        home_attack: toFloat(row['home_attack']),
        away_attack: toFloat(row['away_attack']),
        home_shots: toFloat(row['home_shots']),
        away_shots: toFloat(row['away_shots']),
        time: row['time'] ?? '',
        date: row['date'] ?? '',
        ht_result: row['ht_result'] ?? '',
        at_result: row['at_result'] ?? '',
        total_corners: toFloat(row['total_corners']),
      }),
    );
  }

  private loadHistoricalMatches(): Promise<HistoricalMatch[]> {
    return parseCsv(
      path.join(this.dataDir, 'novo_campeonato_brasileiro.csv'),
      (row) => ({
        id: row['ID'] ?? '',
        date: row['Data'] ?? '',
        year: toInt(row['Ano']),
        round: toInt(row['Rodada']),
        home_team: row['Equipe_mandante'] ?? '',
        away_team: row['Equipe_visitante'] ?? '',
        home_goals: toInt(row['Gols_mandante']),
        away_goals: toInt(row['Gols_visitante']),
        home_state: row['Mandante_UF'] ?? '',
        away_state: row['Visitante_UF'] ?? '',
        winner: row['Vencedor'] ?? '',
        arena: row['Arena'] ?? '',
      }),
    );
  }

  private loadFifaPlayers(): Promise<FifaPlayer[]> {
    return parseCsv(
      path.join(this.dataDir, 'fifa_data.csv'),
      (row) => {
        const id = toInt(row['ID']);
        if (id === 0 && !row['Name']) return null;
        return {
          id,
          name: row['Name'] ?? '',
          age: toInt(row['Age']),
          nationality: row['Nationality'] ?? '',
          overall: toInt(row['Overall']),
          potential: toInt(row['Potential']),
          club: row['Club'] ?? '',
          position: row['Position'] ?? '',
          jersey_number: row['Jersey Number'] ?? row['Jersey Num'] ?? '',
          height: row['Height'] ?? '',
          weight: row['Weight'] ?? '',
        };
      },
    );
  }

  private normalizeDateStr(dateStr: string): string {
    const d = parseDate(dateStr);
    return d ? formatDate(d) : dateStr;
  }

  private buildNormalized(): NormalizedMatch[] {
    const seen = new Set<string>();
    const result: NormalizedMatch[] = [];

    const add = (m: NormalizedMatch): void => {
      // Dedup key: date + normalized teams + competition (ignores minor team name diffs)
      const key = `${m.date}|${m.home_team.toLowerCase()}|${m.away_team.toLowerCase()}|${m.competition.toLowerCase()}`;
      if (seen.has(key)) return;
      seen.add(key);
      result.push(m);
    };

    // Store raw team names to preserve disambiguating state suffixes (e.g. Atletico-MG vs Atletico-PR).
    // teamsMatch() handles fuzzy matching at query time.
    const trim = (s: string) => s.trim().replace(/^"|"$/g, '');

    // Priority 1: primary sources (Brasileirão 2012-2022, Copa do Brasil, Libertadores)
    for (const m of this.brasileiraoMatches) {
      add({
        date: this.normalizeDateStr(m.datetime),
        home_team: trim(m.home_team),
        away_team: trim(m.away_team),
        home_goals: m.home_goal,
        away_goals: m.away_goal,
        competition: 'Brasileirão',
        season: m.season,
        round: m.round,
        source: 'brasileirao',
      });
    }

    for (const m of this.cupMatches) {
      add({
        date: this.normalizeDateStr(m.datetime),
        home_team: trim(m.home_team),
        away_team: trim(m.away_team),
        home_goals: m.home_goal,
        away_goals: m.away_goal,
        competition: 'Copa do Brasil',
        season: m.season,
        round: m.round,
        source: 'cup',
      });
    }

    for (const m of this.libertadoresMatches) {
      add({
        date: this.normalizeDateStr(m.datetime),
        home_team: trim(m.home_team),
        away_team: trim(m.away_team),
        home_goals: m.home_goal,
        away_goals: m.away_goal,
        competition: 'Copa Libertadores',
        season: m.season,
        stage: m.stage,
        source: 'libertadores',
      });
    }

    // Priority 2: historical matches (Brasileirão 2003-2011, before brasileirao source starts)
    for (const m of this.historicalMatches) {
      if (m.year >= 2012) continue; // covered by brasileirao source
      const dateNorm = this.normalizeDateStr(m.date);
      add({
        date: dateNorm,
        home_team: trim(m.home_team),
        away_team: trim(m.away_team),
        home_goals: m.home_goals,
        away_goals: m.away_goals,
        competition: 'Brasileirão',
        season: m.year,
        round: m.round,
        source: 'historical',
      });
    }

    // Priority 3: extended dataset — only for years not covered by primary sources
    // brasileirao covers Serie A 2012-2022; cup covers Copa do Brasil 2012-2021
    // Skip Copa Libertadores entirely (dedicated source has it)
    for (const m of this.extendedMatches) {
      if (!m.date || !m.home || !m.away) continue;
      const dateNorm = this.normalizeDateStr(m.date);
      const seasonYear = parseInt(dateNorm.substring(0, 4), 10);
      if (isNaN(seasonYear)) continue;

      if (m.tournament === 'Serie A' && seasonYear <= 2022) continue;
      if (m.tournament === 'Copa do Brasil' && seasonYear <= 2021) continue;

      const comp = m.tournament === 'Serie A' ? 'Brasileirão'
        : m.tournament === 'Serie B' ? 'Brasileirão Série B'
        : m.tournament === 'Serie C' ? 'Brasileirão Série C'
        : m.tournament;
      add({
        date: dateNorm,
        home_team: trim(m.home),
        away_team: trim(m.away),
        home_goals: Math.round(m.home_goal),
        away_goals: Math.round(m.away_goal),
        competition: comp,
        season: seasonYear,
        source: 'extended',
      });
    }

    return result;
  }

  getBrasileiraoMatches(): BrasileiraoMatch[] { return this.brasileiraoMatches; }
  getCupMatches(): CupMatch[] { return this.cupMatches; }
  getLibertadoresMatches(): LibertadoresMatch[] { return this.libertadoresMatches; }
  getExtendedMatches(): ExtendedMatch[] { return this.extendedMatches; }
  getHistoricalMatches(): HistoricalMatch[] { return this.historicalMatches; }
  getPlayers(): FifaPlayer[] { return this.fifaPlayers; }
  getAllNormalizedMatches(): NormalizedMatch[] { return this.allNormalized; }
}
