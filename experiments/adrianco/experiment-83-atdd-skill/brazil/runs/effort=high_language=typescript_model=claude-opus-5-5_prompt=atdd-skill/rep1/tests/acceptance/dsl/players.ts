/**
 * DSL: finding players and summarising squads.
 */
import type { PlayerCriteria, PlayerRecord, SoccerDriver } from '../drivers/soccer-driver.js';

export class PlayersDsl {
  constructor(private readonly driver: SoccerDriver) {}

  async lookUp({ name }: { name: string }): Promise<void> {
    await this.driver.lookUpPlayer(name);
  }

  confirmPlayer(expected: Partial<Pick<PlayerRecord, 'name' | 'club' | 'overall' | 'position' | 'nationality'>>): void {
    this.driver.confirmPlayer(expected);
  }

  confirmSkills(expected: Record<string, number>): void {
    this.driver.confirmSkills(expected);
  }

  confirmNotFound({ suggesting }: { suggesting: string }): void {
    this.driver.confirmPlayerNotFound(suggesting);
  }

  async search(criteria: PlayerCriteria): Promise<void> {
    await this.driver.searchPlayers(criteria);
  }

  /** Exactly these players; best rated first unless told otherwise. */
  confirmListed(names: string[], { inAnyOrder = false }: { inAnyOrder?: boolean } = {}): void {
    this.driver.confirmPlayersListed(names, inAnyOrder);
  }

  async summariseByBrazilianClub({ nationality = 'Brazil' }: { nationality?: string } = {}): Promise<void> {
    await this.driver.summariseClubsForNationality(nationality);
  }

  confirmClubSummary(expected: { club: string; players?: number; averageRating?: number }): void {
    this.driver.confirmClubSummary(expected);
  }

  confirmClubNotInSummary(club: string): void {
    this.driver.confirmClubNotInSummary(club);
  }
}
