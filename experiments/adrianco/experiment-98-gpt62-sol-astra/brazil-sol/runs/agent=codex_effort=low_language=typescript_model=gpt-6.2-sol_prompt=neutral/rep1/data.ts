import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse } from 'csv-parse/sync';

export const sources = {
  league: 'Brasileirao_Matches.csv',
  historical: 'novo_campeonato_brasileiro.csv',
  cup: 'Brazilian_Cup_Matches.csv',
  libertadores: 'Libertadores_Matches.csv',
  extended: 'BR-Football-Dataset.csv',
  players: 'fifa_data.csv',
} as const;

export const competitions = {
  league: 'Brasileirão Série A',
  serieB: 'Brasileirão Série B',
  serieC: 'Brasileirão Série C',
  cup: 'Copa do Brasil',
  libertadores: 'Copa Libertadores',
} as const;

export function normalize(value: string): string {
  return value.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ').trim();
}

const teamGroups = [
  ['Flamengo', 'Flamengo RJ', 'Clube de Regatas do Flamengo', 'CR Flamengo'],
  ['Fluminense', 'Fluminense RJ', 'Fluminense FC', 'Fluminense Football Club'],
  ['Corinthians', 'Corinthians SP', 'SC Corinthians', 'Sport Club Corinthians Paulista'],
  ['Palmeiras', 'Palmeiras SP', 'SE Palmeiras', 'Sociedade Esportiva Palmeiras'],
  ['São Paulo', 'Sao Paulo SP', 'Sao Paulo FC', 'Sao Paulo Futebol Clube', 'SPFC'],
  ['Santos', 'Santos SP', 'Santos FC', 'Santos Futebol Clube'],
  ['Vasco da Gama', 'Vasco', 'Vasco RJ', 'Vasco da Gama RJ', 'CR Vasco da Gama', 'Club de Regatas Vasco da Gama'],
  ['Athletico Paranaense', 'Atletico PR', 'Athletico PR', 'Atletico Paranaense', 'Athletico', 'Athletico Paranaense PR', 'Atletico Paranaense PR', 'Club Athletico Paranaense'],
  ['Atlético Mineiro', 'Atletico MG', 'Atletico Mineiro MG', 'Clube Atletico Mineiro'],
  ['Atlético Goianiense', 'Atletico GO', 'Atletico Goianiense GO', 'Atletico Clube Goianiense'],
  ['América Mineiro', 'America MG', 'America FC Minas Gerais', 'America Mineiro MG', 'America Mineiro', 'America Futebol Clube MG'],
  ['América-RN', 'America FC Natal', 'America de Natal'],
  ['Botafogo-RJ', 'Botafogo', 'Botafogo FR', 'Botafogo de Futebol e Regatas'],
  ['Grêmio', 'Gremio RS', 'Gremio FBPA', 'Gremio Foot Ball Porto Alegrense'],
  ['Internacional', 'Internacional RS', 'SC Internacional', 'Sport Club Internacional'],
  ['Bahia', 'Bahia BA', 'EC Bahia', 'Esporte Clube Bahia'],
  ['Vitória', 'Vitoria BA', 'EC Vitoria', 'Vitoria EC', 'Esporte Clube Vitoria'],
  ['Sport Recife', 'Sport', 'Sport PE', 'Sport Club do Recife', 'Sport Recife PE'],
  ['Fortaleza', 'Fortaleza CE', 'Fortaleza EC', 'Fortaleza FC', 'Fortaleza Esporte Clube'],
  ['Ceará', 'Ceara CE', 'Ceara SC', 'Ceara Sporting Club'],
  ['Coritiba', 'Coritiba PR', 'Coritiba FC', 'Coritiba Foot Ball Club'],
  ['Cruzeiro', 'Cruzeiro MG', 'Cruzeiro EC', 'Cruzeiro Esporte Clube'],
  ['Red Bull Bragantino', 'Red Bull Bragantino SP', 'Bragantino', 'Bragantino SP', 'RB Bragantino'],
  ['Santa Cruz', 'Santa Cruz PE', 'Santa Cruz FC'],
  ['Paraná', 'Parana PR', 'CA Parana', 'Parana Clube'],
  ['Náutico', 'Nautico PE', 'Nautico Capibaribe', 'Clube Nautico Capibaribe'],
  ['Juventude', 'Juventude RS', 'EC Juventude'],
  ['Portuguesa', 'Portuguesa SP', 'Portuguesa Desportos'],
  ['ABC', 'ABC RN', 'A B C RN'],
  ['Guarani', 'Guarani SP'],
  ['Cuiabá', 'Cuiaba MT'],
  ['CSA', 'CSA AL', 'CS Alagoano'],
  ['Avaí', 'Avai SC'], ['Chapecoense', 'Chapecoense SC'], ['Criciúma', 'Criciuma SC'],
  ['Goiás', 'Goias GO'], ['Figueirense', 'Figueirense SC'], ['Joinville', 'Joinville SC'],
  ['Ponte Preta', 'Ponte Preta SP'], ['Paysandu', 'Paysandu PA'], ['São Caetano', 'Sao Caetano SP'],
  ['Confiança', 'Confianca SE', 'AD Confianca'], ['Remo', 'Remo PA', 'Clube do Remo'],
  ['Santo André', 'Santo Andre SP'],
  ['Boavista-RJ', 'Boavista', 'Boavista SC Saquarema', 'Boavista Sport Club antigo Esporte Clube Barreira RJ'],
  ['Afogados', 'Afogados PE', 'Afogados da Ingazeira FC'],
  ['4 de Julho', '4 de Julho PI', '4 de Julho EC'],
  ['Ferroviário-CE', 'Ferroviario'],
  ['Altos', 'AE Altos', 'Altos PI'],
  ['Sampaio Corrêa', 'Sampaio Correa MA'],
  ['Operário-PR', 'Operario Ferroviario Esporte C PR'],
  ['Madureira-RJ', 'Madureira EC'],
  ['Moto Clube', 'Moto Club de Sao Luis', 'Moto Clube MA'],
  ['São José-PA', 'Sao Jose PA'],
  ['São José-RS', 'Sao Jose RS', 'Sao Jose POA'],
  ['Botafogo-PB', 'Botafogo PB'], ['Botafogo-SP', 'Botafogo SP'],
  ['River-PI', 'River AC'], ['Gama', 'Gama DF', 'SE Gama'],
  ['Campinense', 'Campinense PB', 'Campinense Clube'],
  ['Sinop', 'Sinop MT', 'Sinop FC'], ['Sergipe', 'Sergipe SE', 'CS Sergipe'],
  ['Fluminense de Feira', 'Fluminense de Feira BA'],
  ['Independente-PA'], ['ASA', 'ASA AL'], ['Dom Bosco', 'Dom Bosco MT', 'CE Dom Bosco'],
  ['Toledo', 'Toledo PR', 'Toledo EC'], ['Votuporanguense', 'Votuporanguense SP', 'CA Votuporanguense'],
  ['Fast Clube', 'Fast AM', 'Fast Clube AM'], ['Palmas', 'Palmas TO', 'Palmas FR'],
  ['URT', 'URT MG'], ['Nacional-AM'],
  ['Foz do Iguaçu', 'Foz do Iguacu PR'], ['Vitória-ES', 'Vitoria ES'],
  ['Brasil de Pelotas', 'Brasil de Pelotas RS', 'Brasil RS'],

  ...[
    ['CRB', 'AL'], ['Luverdense', 'MT'], ['Cianorte', 'PR'], ['Londrina', 'PR'],
    ['Brusque', 'SC'], ['Uberlândia', 'MG'], ['Vila Nova', 'GO'], ['Boa', 'MG'],
    ['Aparecidense', 'GO'], ['Tubarão', 'SC'], ['Novo Hamburgo', 'RS'], ['Salgueiro', 'PE'],
    ['Corumbaense', 'MS'], ['Lagarto', 'SE'], ['Inter de Limeira', 'SP'], ['Oeste', 'SP'],
    ['Ituano', 'SP'], ['Juazeirense', 'BA'], ['Manaus', 'AM'], ['Genus', 'RO'], ['Aquidauanense', 'MS'],
    ['Anapolina', 'GO'], ['Lajeadense', 'RS'], ['Coruripe', 'AL'], ['Imperatriz', 'MA'],
    ['Jacuipense', 'BA'], ['Icasa', 'CE'], ['Globo', 'RN'],
    ['Mixto', 'MT'], ['Luziania', 'DF'], ['Estanciano', 'SE'], ['Goianesia', 'GO'],
    ['Linense', 'SP'], ['Bangu', 'RJ'], ['Volta Redonda', 'RJ'], ['Sobradinho', 'DF'],
    ['Caucaia', 'CE'], ['Itabaiana', 'SE'], ['XV Piracicaba', 'SP'], ['Tombense', 'MG'],
  ].map(([name, state]) => [name, `${name} ${state}`]),
];

export const teamAliases = new Map(teamGroups.flatMap(([team, ...aliases]) =>
  [team, ...aliases].map(alias => [normalize(alias), team] as const)));

export function teamName(value: string): string {
  return teamAliases.get(normalize(value)) ?? value.trim();
}

export function dateOnly(value: string): string | null {
  const iso = /^(\d{4})-(\d{2})-(\d{2})(?:$|[ T])/.exec(value);
  const brazilian = /^(\d{2})\/(\d{2})\/(\d{4})(?:$|[ T])/.exec(value);
  const date = iso ? `${iso[1]}-${iso[2]}-${iso[3]}`
    : brazilian ? `${brazilian[3]}-${brazilian[2]}-${brazilian[1]}` : null;
  if (!date) return null;
  const parsed = new Date(date);
  return Number.isFinite(+parsed) && parsed.toISOString().startsWith(date) ? date : null;
}

function numeric(value: string): number | null {
  return value?.trim() && Number.isFinite(Number(value)) ? Number(value) : null;
}

export type Competition = keyof typeof competitions;
export type MatchSource = Exclude<keyof typeof sources, 'players'>;

export interface Match {
  date: string | null;
  time: string | null;
  competition: Competition;
  season: number | null;
  home: string;
  away: string;
  homeGoals: number | null;
  awayGoals: number | null;
  round: number | null;
  stage: string | null;
  stadium: string | null;
  sources: MatchSource[];
  statistics?: Record<string, number | string | null>;
}

export interface Player {
  id: number;
  name: string;
  nationality: string;
  club: string;
  position: string;
  overall: number;
  potential: number;
  age: number;
  jerseyNumber: number | null;
  height: string;
  weight: string;
  attributes: Record<string, number | null>;
}

const extendedCompetitions: Record<string, Competition> = {
  'Serie A': 'league', 'Serie B': 'serieB', 'Serie C': 'serieC', 'Copa do Brasil': 'cup',
};

function readMatch(row: Record<string, string>, source: MatchSource): Match {
  const datetime = row.datetime ?? row.Data ?? row.date;
  const date = dateOnly(datetime);
  const competition = source === 'extended' ? extendedCompetitions[row.tournament]
    : source === 'historical' ? 'league' : source;
  let season = numeric(row.season ?? row.Ano);
  if (source === 'extended' && date) {
    season = Number(date.slice(0, 4));
    // COVID-delayed 2020 competitions reached into the next calendar year.
    const endOf2020 = {
      league: '2021-02-26', serieB: '2021-01-31', serieC: '2021-01-31', cup: '2021-03-08',
    } as const;
    if (competition !== 'libertadores' && date >= '2021-01-01' && date <= endOf2020[competition]) {
      season = 2020;
    }
  }
  return {
    date, time: row.time || datetime.match(/\d{2}:\d{2}:\d{2}$/)?.[0] || null,
    competition, season,
    home: teamName(row.home_team ?? row.Equipe_mandante ?? row.home),
    away: teamName(row.away_team ?? row.Equipe_visitante ?? row.away),
    homeGoals: numeric(row.home_goal ?? row.Gols_mandante),
    awayGoals: numeric(row.away_goal ?? row.Gols_visitante),
    round: numeric(row.round ?? row.Rodada),
    stage: row.stage || null,
    stadium: row.Arena || null,
    sources: [source],
    statistics: source === 'extended' ? Object.fromEntries(
      ['home_corner', 'away_corner', 'home_attack', 'away_attack', 'home_shots',
        'away_shots', 'ht_diff', 'at_diff', 'total_corners', 'ht_result', 'at_result']
        .map(key => [key, key.endsWith('_result') ? row[key] || null : numeric(row[key])]),
    ) : undefined,
  };
}

function labelCupStages(rows: Match[]): void {
  const finalsBySeason = new Map<number, number>([
    [2012, 6], [2013, 8], [2014, 8], [2015, 8], [2016, 7],
    [2017, 8], [2018, 8], [2019, 8], [2020, 8], [2021, 7],
  ]);
  for (const row of rows) {
    const finalRound = finalsBySeason.get(row.season ?? 0);
    if (row.round === null || finalRound === undefined) continue;
    row.stage = ['final', 'semifinals', 'quarterfinals', 'round of 16'][finalRound - row.round] ?? null;
  }
}

function reconcile(raw: Record<MatchSource, Match[]>): Match[] {
  const byFixture = new Map<string, Match[]>();
  for (const source of ['league', 'historical', 'cup', 'libertadores', 'extended'] as const) {
    for (const row of raw[source]) {
      const key = [row.competition, row.season, normalize(row.home), normalize(row.away)].join('|');
      const candidates = byFixture.get(key) ?? [];
      const available = candidates.filter(other => !other.sources.includes(source));
      const distance = (other: Match) => row.date && other.date
        ? Math.abs(Date.parse(row.date) - Date.parse(other.date)) / 86_400_000 : Infinity;
      const match = available.find(other => row.competition === 'league' || distance(other) <= 1) ??
        available.find(other => row.competition === 'cup' && other.homeGoals === null && distance(other) <= 7);
      if (!match) {
        candidates.push({ ...row, sources: [...row.sources] });
        byFixture.set(key, candidates);
        continue;
      }
      match.sources.push(source);
      if (match.homeGoals === null && row.homeGoals !== null) {
        match.date = row.date ?? match.date;
        match.time = row.time ?? match.time;
      }
      match.stadium ??= row.stadium;
      match.statistics ??= row.statistics;
      match.stage ??= row.stage;
      if ((match.homeGoals === null || match.awayGoals === null) && row.homeGoals !== null && row.awayGoals !== null) {
        match.homeGoals = row.homeGoals;
        match.awayGoals = row.awayGoals;
      }
    }
  }
  const leagueSeasons = new Set([...raw.league, ...raw.historical].map(row => row.season));
  // The extended feed contains mislabeled league rows. Keep them available through source queries.
  return [...byFixture.values()].flat().filter(row =>
    row.competition !== 'league' || !leagueSeasons.has(row.season) ||
    row.sources.includes('league') || row.sources.includes('historical'));
}

const defaultDirectory = fileURLToPath(new URL('../data/kaggle/', import.meta.url));

export function loadData(directory = defaultDirectory) {
  const read = (source: keyof typeof sources): Record<string, string>[] => parse(
    readFileSync(join(directory, sources[source]), 'utf8'),
    { columns: true, bom: true, skip_empty_lines: true },
  );
  const raw = {
    league: read('league').map(row => readMatch(row, 'league')),
    historical: read('historical').map(row => readMatch(row, 'historical')),
    cup: read('cup').map(row => readMatch(row, 'cup')),
    libertadores: read('libertadores').map(row => readMatch(row, 'libertadores')),
    extended: read('extended').map(row => readMatch(row, 'extended')),
  };
  labelCupStages(raw.cup);
  for (const year of [2021, 2022, 2023]) {
    const cup = raw.extended.filter(row => row.competition === 'cup' && row.season === year)
      .sort((a, b) => (b.date ?? '').localeCompare(a.date ?? ''));
    const [last, previous] = cup;
    if (last && previous && last.home === previous.away && last.away === previous.home) {
      last.stage = previous.stage = 'final';
    }
  }
  const players: Player[] = read('players').map(row => {
    const columns = Object.keys(row);
    return {
      id: Number(row.ID), name: row.Name, nationality: row.Nationality, club: row.Club,
      position: row.Position, overall: Number(row.Overall), potential: Number(row.Potential),
      age: Number(row.Age), jerseyNumber: numeric(row['Jersey Number']), height: row.Height, weight: row.Weight,
      attributes: Object.fromEntries(columns.slice(columns.indexOf('Crossing'), columns.indexOf('GKReflexes') + 1)
        .map(key => [key, numeric(row[key])])),
    };
  });
  const matches = reconcile(raw);
  // The file's trailing fixture follows the 2022 semifinals and names their winners.
  const undatedFinal = matches.find(match => match.competition === 'libertadores' &&
    match.season === null && match.stage === 'final' &&
    match.home === 'Flamengo' && match.away === 'Athletico Paranaense');
  if (undatedFinal) undatedFinal.season = 2022;
  return { raw, matches, players };
}
