/**
 * DSL: the football world a spec starts from.
 *
 * Specs describe only the matches and players they care about; everything
 * else gets a sensible default here, so specs stay short. Each spec gets a
 * fresh system holding only the data it describes (functional isolation).
 */
import type { Dataset, SoccerDriver } from '../drivers/soccer-driver.js';
import { parseScore } from './notation.js';

const DATASET_FOR_COMPETITION: Record<string, Dataset> = {
  'Brasileirão': 'brasileirao',
  'Copa do Brasil': 'cup',
  'Libertadores': 'libertadores',
  'Serie B': 'extended',
  'Serie C': 'extended',
};

const COMPETITION_FOR_DATASET: Record<Dataset, string> = {
  brasileirao: 'Brasileirão',
  historical: 'Brasileirão',
  extended: 'Brasileirão',
  cup: 'Copa do Brasil',
  libertadores: 'Libertadores',
};

export interface MatchParams {
  home?: string;
  away?: string;
  score?: string;
  date?: string;
  season?: number;
  competition?: string;
  round?: number;
  stage?: string;
  dataset?: Dataset;
  corners?: string;
  shots?: string;
}

export interface PlayerParams {
  name?: string;
  club?: string;
  nationality?: string;
  overall?: number;
  potential?: number;
  position?: string;
  age?: number;
  [skill: string]: string | number | undefined;
}

export class GivenDsl {
  private sequence = 0;

  constructor(private readonly driver: SoccerDriver) {}

  match({
    home = `Home Side ${this.next()}`,
    away = `Away Side ${this.next()}`,
    score = '1-0',
    season,
    date,
    dataset,
    competition = dataset ? COMPETITION_FOR_DATASET[dataset] : 'Brasileirão',
    round = 1,
    stage = 'group stage',
    corners,
    shots,
  }: MatchParams = {}): void {
    const matchDate = date ?? this.dateIn(season ?? 2016);
    const [homeGoals, awayGoals] = parseScore(score);
    this.driver.recordMatch({
      home,
      away,
      homeGoals,
      awayGoals,
      date: matchDate,
      season: season ?? Number(matchDate.slice(0, 4)),
      competition,
      round,
      stage,
      dataset: dataset ?? DATASET_FOR_COMPETITION[competition] ?? 'extended',
      corners: corners ? parseScore(corners) : undefined,
      shots: shots ? parseScore(shots) : undefined,
    });
  }

  /**
   * A complete double round-robin league season whose final table comes out
   * in exactly the given order: each team beats every team below it at home
   * and draws the return fixture.
   */
  leagueSeason({ season, finishingOrder, competition = 'Brasileirão' }: { season: number; finishingOrder: string[]; competition?: string }): void {
    finishingOrder.forEach((higher, i) => {
      finishingOrder.slice(i + 1).forEach((lower) => {
        this.match({ home: higher, away: lower, score: '2-0', season, competition });
        this.match({ home: lower, away: higher, score: '1-1', season, competition });
      });
    });
  }

  player({
    name = `Player ${this.next()}`,
    club = 'Santos',
    nationality = 'Brazil',
    overall = 70,
    potential,
    position = 'CM',
    age = 25,
    ...skills
  }: PlayerParams = {}): void {
    this.driver.recordPlayer({
      name,
      club,
      nationality,
      overall,
      potential: potential ?? overall,
      position,
      age,
      jerseyNumber: (this.sequence % 98) + 1,
      skills: Object.fromEntries(Object.entries(skills).map(([k, v]) => [k, Number(v)])),
    });
  }

  private next(): number {
    return ++this.sequence;
  }

  /** A distinct date within the season, so generated matches never collide. */
  private dateIn(season: number): string {
    const day = new Date(Date.UTC(season, 4, 1 + this.next() * 2));
    return day.toISOString().slice(0, 10);
  }
}
