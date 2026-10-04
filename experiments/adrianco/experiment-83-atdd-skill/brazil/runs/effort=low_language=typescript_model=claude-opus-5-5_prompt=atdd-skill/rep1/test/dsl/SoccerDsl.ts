import { McpSoccerDriver } from "../drivers/McpSoccerDriver";

// DSL: domain vocabulary for the specs; named params with defaults, delegates to the protocol driver.
export class SoccerDsl {
  private driver = new McpSoccerDriver();

  start() { return this.driver.connect(); }
  stop() { return this.driver.disconnect(); }

  askForMatchesBetween({ team, opponent, season }: { team: string; opponent: string; season?: number }) {
    return this.driver.ask("search_matches", { team, opponent, season });
  }
  askForMatchesOf({ team, season, competition }: { team: string; season?: number; competition?: string }) {
    return this.driver.ask("search_matches", { team, season, competition });
  }
  askForMatchesIn({ competition, stage, from, to }: { competition: string; stage?: string; from?: string; to?: string }) {
    return this.driver.ask("search_matches", { competition, stage, from, to });
  }
  askForLastMeeting({ team, opponent }: { team: string; opponent: string }) {
    return this.driver.ask("last_meeting", { team, opponent });
  }
  askForDerbies({ season }: { season?: number }) {
    return this.driver.ask("derbies", { season });
  }
  askForTeamRecord({ team, season, venue = "all", competition = "Brasileirão" }:
    { team: string; season?: number; venue?: "home" | "away" | "all"; competition?: string }) {
    return this.driver.ask("team_record", { team, season, venue, competition });
  }
  askForHeadToHead({ team, opponent }: { team: string; opponent: string }) {
    return this.driver.ask("head_to_head", { team, opponent });
  }
  askForCompetitionsOf({ team }: { team: string }) {
    return this.driver.ask("team_competitions", { team });
  }
  askForPlayer({ name }: { name: string }) {
    return this.driver.ask("search_players", { name });
  }
  askForPlayers({ nationality, club, position, limit = 20 }:
    { nationality?: string; club?: string; position?: string; limit?: number }) {
    return this.driver.ask("search_players", { nationality, club, position, limit });
  }
  askForStandings({ season }: { season: number }) {
    return this.driver.ask("standings", { season });
  }
  askForTopScoringTeam({ season }: { season: number }) {
    return this.driver.ask("top_scoring_teams", { season });
  }
  askForCompetitionStats({ competition, season }: { competition?: string; season?: number }) {
    return this.driver.ask("competition_stats", { competition, season });
  }
  askForBiggestWins({ limit = 10, competition }: { limit?: number; competition?: string }) {
    return this.driver.ask("biggest_wins", { limit, competition });
  }
  askForBestRecord({ venue = "home", season }: { venue?: "home" | "away" | "all"; season?: number }) {
    return this.driver.ask("best_record", { venue, season });
  }
  askToCompareSeasons({ first, second }: { first: number; second: number }) {
    return this.driver.ask("compare_seasons", { seasons: [first, second] });
  }

  confirmMatchesListed({ atLeast = 1 }: { atLeast?: number } = {}) { this.driver.assertMatchesListed(atLeast); }
  confirmPlayersListed({ atLeast = 1 }: { atLeast?: number } = {}) { this.driver.assertPlayersListed(atLeast); }
  confirmAnswerMentions(...phrases: string[]) { this.driver.assertMentions(phrases); }
  confirmAnswerHasScore() { this.driver.assertHasScore(); }
  confirmRecord({ matches }: { matches: number }) { this.driver.assertRecordMatches(matches); }
  confirmTopPlayerIs(name: string) { this.driver.assertTopPlayer(name); }
  confirmChampion({ team, points }: { team: string; points?: number }) { this.driver.assertChampion(team, points); }
  confirmRelegatedCount(n: number) { this.driver.assertRelegatedCount(n); }
  confirmSameAnswerFor(variantA: string, variantB: string) {
    return this.driver.assertSameMatchCount(variantA, variantB);
  }
  confirmAllDatasetsLoaded(count: number) { return this.driver.assertDatasetsLoaded(count); }
  async confirmAnsweredWithin(ms: number, action: () => Promise<unknown>) {
    const start = Date.now();
    await action();
    this.driver.assertElapsed(Date.now() - start, ms);
  }
}
