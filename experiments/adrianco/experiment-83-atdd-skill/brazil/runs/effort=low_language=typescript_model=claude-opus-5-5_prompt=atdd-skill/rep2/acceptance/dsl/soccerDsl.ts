import { expect } from "vitest";
import { McpDriver } from "../drivers/mcpDriver";

const plain = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const same = (a: string, b: string) => plain(a).startsWith(plain(b));

class Matches {
  constructor(private d: McpDriver) {}
  findBetween({ team, opponent }: { team: string; opponent: string }) { return this.d.call("search_matches", { team, opponent, limit: 500 }); }
  findForTeam({ team, season, from, to }: { team: string; season?: number; from?: string; to?: string }) {
    return this.d.call("search_matches", { team, season, from, to, limit: 500 });
  }
  findForCompetition({ competition, season, stage }: { competition: string; season?: number; stage?: string }) {
    return this.d.call("search_matches", { competition, season, stage, limit: 500 });
  }
  findLastMeeting({ team, opponent }: { team: string; opponent: string }) { return this.d.call("last_meeting", { team, opponent }); }

  confirmIncludes({ home, away }: { home: string; away: string }) {
    expect(this.d.last.data.matches.some((m: any) => same(m.home, home) && same(m.away, away)), `no ${home} v ${away}`).toBe(true);
  }
  confirmHeadToHeadSummaryShown() { expect(this.d.last.text).toMatch(/Head-to-head in dataset: .* wins, .* wins, \d+ draws/); }
  confirmAllInSeason(season: number) {
    const ms = this.d.last.data.matches;
    expect(ms.length).toBeGreaterThan(0);
    expect(ms.every((m: any) => m.season === season)).toBe(true);
  }
  confirmAllFromCompetition(c: string) {
    const ms = this.d.last.data.matches;
    expect(ms.length).toBeGreaterThan(0);
    expect(ms.every((m: any) => m.competition === c)).toBe(true);
  }
  confirmAllBetweenDates(from: string, to: string) {
    const ms = this.d.last.data.matches;
    expect(ms.length).toBeGreaterThan(0);
    expect(ms.every((m: any) => m.date >= from && m.date <= to)).toBe(true);
  }
  confirmScoreShown() { expect(this.d.last.text).toMatch(/\d{4}-\d{2}-\d{2}: .+ \d+-\d+ .+/); }
}

class Teams {
  constructor(private d: McpDriver) {}
  requestRecord({ team, season, competition, venue = "any" }: { team: string; season?: number; competition?: string; venue?: string }) {
    return this.d.call("team_record", { team, season, competition, venue });
  }
  compareHeadToHead({ team, opponent }: { team: string; opponent: string }) { return this.d.call("head_to_head", { team, opponent }); }
  requestCompetitions({ team }: { team: string }) { return this.d.call("team_competitions", { team }); }
  requestProfile({ team }: { team: string }) { return this.d.call("team_profile", { team }); }

  confirmRecord({ matches }: { matches: number }) {
    const r = this.d.last.data.record;
    expect(r.matches).toBe(matches);
    expect(r.wins + r.draws + r.losses).toBe(matches);
  }
  confirmRecordFor(team: string) {
    expect(this.d.last.data.record.team).toBe(team);
    expect(this.d.last.data.record.matches).toBeGreaterThan(0);
  }
  confirmHeadToHeadNamesBothTeams(a: string, b: string) {
    const h = this.d.last.data;
    expect(same(h.team, a) && same(h.opponent, b)).toBe(true);
    expect(h.matches).toBe(h.teamWins + h.opponentWins + h.draws);
    expect(h.matches).toBeGreaterThan(0);
  }
  confirmCompetitions(cs: string[]) {
    const got = this.d.last.data.competitions.map((c: any) => c.competition);
    for (const c of cs) expect(got).toContain(c);
  }
  confirmProfileHasPlayers() { expect(this.d.last.data.players.length).toBeGreaterThan(0); }
}

class Players {
  constructor(private d: McpDriver) {}
  search(f: { name?: string; nationality?: string; club?: string; position?: string }) { return this.d.call("search_players", { ...f, limit: 50 }); }
  requestNationalityByClub({ nationality }: { nationality: string }) { return this.d.call("players_by_club", { nationality, limit: 50 }); }

  private names() { return this.d.last.data.players.map((p: any) => p.name); }
  confirmFound(name: string) { expect(this.names()).toContain(name); }
  confirmFirstIs(name: string) { expect(this.names()[0]).toBe(name); }
  confirmAllOfNationality(n: string) { expect(this.d.last.data.players.every((p: any) => p.nationality === n)).toBe(true); }
  confirmClubListed(club: string) { expect(this.d.last.data.clubs.map((c: any) => c.club)).toContain(club); }
}

class Competitions {
  constructor(private d: McpDriver) {}
  requestStandings({ season }: { season: number }) { return this.d.call("standings", { season }); }
  requestBracket({ season }: { season: number }) { return this.d.call("libertadores_bracket", { season }); }
  confirmChampion({ team, points }: { team: string; points: number }) {
    const top = this.d.last.data.table[0];
    expect(top.team).toBe(team);
    expect(top.points).toBe(points);
  }
  confirmRelegated(teams: string[]) { expect([...this.d.last.data.relegated].sort()).toEqual([...teams].sort()); }
  confirmBracketHasStage(stage: string) { expect(this.d.last.data.stages.map((s: any) => s.stage)).toContain(stage); }
}

class Stats {
  constructor(private d: McpDriver) {}
  requestOverview({ competition }: { competition?: string }) { return this.d.call("stats_overview", { competition }); }
  requestBiggestWins({ limit = 10 }: { limit?: number }) { return this.d.call("biggest_wins", { limit }); }
  requestBestRecord({ venue }: { venue: "home" | "away" }) { return this.d.call("best_records", { venue }); }
  compareSeasons({ first, second }: { first: number; second: number }) { return this.d.call("compare_seasons", { first, second }); }

  confirmAverageGoalsBetween(lo: number, hi: number) {
    expect(this.d.last.data.averageGoals).toBeGreaterThan(lo);
    expect(this.d.last.data.averageGoals).toBeLessThan(hi);
  }
  confirmWinsListed(n: number) {
    const w = this.d.last.data.wins;
    expect(w).toHaveLength(n);
    const margin = (m: any) => Math.abs(m.homeGoals - m.awayGoals);
    for (let i = 1; i < w.length; i++) expect(margin(w[i - 1])).toBeGreaterThanOrEqual(margin(w[i]));
  }
  confirmRankingShown() { expect(this.d.last.data.ranking.length).toBeGreaterThan(0); }
  confirmSeasonsCompared(a: number, b: number) { expect(this.d.last.data.seasons.map((s: any) => s.season)).toEqual([a, b]); }
  async confirmRespondsWithin(ms: number) {
    await this.d.call("best_records", { venue: "home" });
    expect(this.d.last.elapsedMs).toBeLessThan(ms);
  }
}

export class SoccerDsl {
  matches: Matches; teams: Teams; players: Players; competitions: Competitions; stats: Stats;
  constructor(private driver: McpDriver) {
    this.matches = new Matches(driver); this.teams = new Teams(driver); this.players = new Players(driver);
    this.competitions = new Competitions(driver); this.stats = new Stats(driver);
  }
  stop() { return this.driver.stop(); }
}

export async function startDsl() {
  const d = new McpDriver();
  await d.start();
  return new SoccerDsl(d);
}
