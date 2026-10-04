/**
 * DSL: establishing what the datasets contain.
 *
 * Specs say only what they care about; everything else gets a sensible
 * default (a 1-0 score, the next free match day, the next round number).
 */
import type { WorldRef } from './soccer-dsl.js';
import type { LeagueDataset } from '../drivers/dataset-stub.js';
import { parseScore } from './score.js';

export interface MatchSpec {
  home: string;
  away: string;
  score?: string;
  date?: string;
  season?: number;
}

export class GivenDsl {
  constructor(private readonly world: WorldRef) {}

  async brasileiraoMatch({ recordedIn = 'serie-a-dataset', round, ...match }: MatchSpec & { round?: number; recordedIn?: LeagueDataset }) {
    const m = this.complete(match);
    this.world().stub().recordLeagueMatch({
      ...m,
      dataset: recordedIn,
      division: 'Serie A',
      round: round ?? this.world().next('round'),
    });
  }

  async leagueMatch({ division = 'Serie A', corners, shots, ...match }: MatchSpec & { division?: 'Serie A' | 'Serie B' | 'Serie C'; corners?: string; shots?: string }) {
    const m = this.complete(match);
    this.world().stub().recordLeagueMatch({
      ...m,
      dataset: 'extended-stats-dataset',
      division,
      round: this.world().next('round'),
      corners: corners ? parseScore(corners) : undefined,
      shots: shots ? parseScore(shots) : undefined,
    });
  }

  async copaDoBrasilMatch({ stage, ...match }: MatchSpec & { stage?: string }) {
    this.world().stub().recordCupMatch({ ...this.complete(match), stage });
  }

  async copaDoBrasilTie(tie: TieSpec) {
    for (const leg of this.legs(tie)) await this.copaDoBrasilMatch(leg);
  }

  async libertadoresMatch({ stage = 'group stage', ...match }: MatchSpec & { stage?: string }) {
    this.world().stub().recordLibertadoresMatch({ ...this.complete(match), stage });
  }

  async libertadoresTie(tie: TieSpec) {
    for (const leg of this.legs(tie)) await this.libertadoresMatch(leg);
  }

  /** A double round-robin league season in which every team beats every team listed below it. */
  async brasileiraoSeasonFinishingInOrder({ season, teams }: { season: number; teams: string[] }) {
    for (let i = 0; i < teams.length; i++) {
      for (let j = i + 1; j < teams.length; j++) {
        await this.brasileiraoMatch({ home: teams[i], away: teams[j], score: '1-0', season });
        await this.brasileiraoMatch({ home: teams[j], away: teams[i], score: '0-1', season });
      }
    }
  }

  async player({
    name,
    nationality = 'Brazil',
    club = 'Santos',
    overall = 70,
    potential,
    position = 'CM',
    age = 25,
  }: { name: string; nationality?: string; club?: string; overall?: number; potential?: number; position?: string; age?: number }) {
    this.world().stub().recordPlayer({
      id: 100_000 + this.world().next('player'),
      name,
      nationality,
      club,
      overall,
      potential: potential ?? overall,
      position,
      age,
      jerseyNumber: this.world().next('jersey'),
    });
  }

  private legs({ season, stage, home, away, firstLeg, secondLeg, dates }: TieSpec): Array<MatchSpec & { stage: string }> {
    return [
      { home, away, score: firstLeg, date: dates?.[0], season, stage },
      { home: away, away: home, score: secondLeg, date: dates?.[1], season, stage },
    ];
  }

  private complete({ home, away, score = '1-0', date, season }: MatchSpec) {
    const resolvedDate = date ?? this.nextMatchDay(season);
    const [homeGoals, awayGoals] = parseScore(score);
    return { home, away, homeGoals, awayGoals, date: resolvedDate, season: season ?? Number(resolvedDate.slice(0, 4)) };
  }

  private nextMatchDay(season?: number): string {
    const start = Date.UTC(season ?? 2023, 3, 1);
    const day = this.world().next(`match-day-${season ?? 'any'}`);
    return new Date(start + day * 86_400_000).toISOString().slice(0, 10);
  }
}

export interface TieSpec {
  season: number;
  stage: string;
  home: string;
  away: string;
  firstLeg: string;
  secondLeg: string;
  dates?: [string, string];
}
