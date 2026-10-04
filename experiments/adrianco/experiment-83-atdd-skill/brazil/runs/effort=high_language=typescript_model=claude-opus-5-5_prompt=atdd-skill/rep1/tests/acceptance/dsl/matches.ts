/**
 * DSL: asking about matches, and confirming what was found.
 */
import type { MatchCriteria, SoccerDriver } from '../drivers/soccer-driver.js';
import { parseMatch, parseScore, parseTie } from './notation.js';

export class MatchesDsl {
  constructor(private readonly driver: SoccerDriver) {}

  async findBetween({ team, opponent, competition, season }: { team: string; opponent: string; competition?: string; season?: number }): Promise<void> {
    await this.driver.findMatches({ team, opponent, competition, season });
  }

  async findForTeam(criteria: MatchCriteria & { team: string }): Promise<void> {
    await this.driver.findMatches(criteria);
  }

  async findInCompetition({ competition, season }: { competition: string; season?: number }): Promise<void> {
    await this.driver.findMatches({ competition, season });
  }

  async findLastMeeting({ team, opponent }: { team: string; opponent: string }): Promise<void> {
    await this.driver.findLastMeeting(team, opponent);
  }

  async findFinals({ competition = 'Copa do Brasil', season }: { competition?: string; season?: number } = {}): Promise<void> {
    await this.driver.findFinals(competition, season);
  }

  async findDerbies({ season }: { season?: number } = {}): Promise<void> {
    await this.driver.findDerbies(season);
  }

  /** Exactly these matches, most recent first. */
  confirmFound(matches: string[]): void {
    this.driver.confirmMatchesFound(matches.map(parseMatch));
  }

  confirmPresentedAs(line: string): void {
    this.driver.confirmMatchPresentedAs(line);
  }

  confirmMatchStatistics({ corners, shots }: { corners?: string; shots?: string }): void {
    this.driver.confirmMatchStatistics({
      corners: corners ? parseScore(corners) : undefined,
      shots: shots ? parseScore(shots) : undefined,
    });
  }

  /** Exactly these finals, most recent first. */
  confirmFinals(finals: string[]): void {
    this.driver.confirmFinals(finals.map(parseTie));
  }

  confirmDerbyNamed(name: string): void {
    this.driver.confirmDerbyNamed(name);
  }

  confirmTeamNotRecognised(team: string): void {
    this.driver.confirmTeamNotRecognised(team);
  }
}
