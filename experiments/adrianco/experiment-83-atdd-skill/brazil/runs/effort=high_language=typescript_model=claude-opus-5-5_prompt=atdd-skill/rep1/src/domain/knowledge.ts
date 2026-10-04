/**
 * The Brazilian soccer knowledge base: every question the MCP tools can ask,
 * answered from the loaded datasets. Each answer has human-readable text for
 * the LLM to relay and structured data for precise follow-up.
 */
import { loadData, type LoadedData } from '../data/loader.js';
import { normaliseDate } from '../data/dates.js';
import { fold, pct, round, tokens } from '../text.js';
import {
  COMPETITIONS, DOMESTIC, LEAGUES, parseCompetition, positionsFor, type Competition, type Match, type Player,
} from './model.js';
import { headToHead, leagueTable, recordFor, recordsFor, summarise, type TeamRecord, type Venue } from './records.js';
import { parseTeamName, BRAZILIAN_STATES } from './teams.js';
import { derbyName } from './derbies.js';

export interface Answer {
  text: string;
  data: Record<string, unknown>;
}

/** A question that cannot be answered as asked (unknown team, bad competition…). */
export class QueryError extends Error {
  constructor(message: string, readonly data: Record<string, unknown>) {
    super(message);
  }
}

const KNOCKOUT_ORDER = ['round of 16', 'quarterfinals', 'semifinals', 'final'];

const DEMONYMS: Record<string, string> = {
  brazilian: 'brazil', brasileiro: 'brazil', brasil: 'brazil', argentine: 'argentina', argentinian: 'argentina',
  uruguayan: 'uruguay', colombian: 'colombia', chilean: 'chile', paraguayan: 'paraguay', peruvian: 'peru',
  ecuadorian: 'ecuador', venezuelan: 'venezuela', bolivian: 'bolivia', mexican: 'mexico', portuguese: 'portugal',
  spanish: 'spain', french: 'france', german: 'germany', italian: 'italy', english: 'england', dutch: 'netherlands',
  belgian: 'belgium',
};

/** A double round-robin league of n teams has n × (n − 1) matches. */
function completeness(teams: number, matches: number): { complete: boolean; missingMatches: number } {
  const missingMatches = Math.max(0, teams * (teams - 1) - matches);
  return { complete: missingMatches === 0, missingMatches };
}

function byDateDesc(a: Match, b: Match): number {
  return b.date.localeCompare(a.date) || (b.time ?? '').localeCompare(a.time ?? '');
}

export interface MatchQuery {
  team?: string;
  opponent?: string;
  venue?: 'home' | 'away' | 'all';
  competition?: string;
  season?: number;
  date_from?: string;
  date_to?: string;
  limit?: number;
}

export class SoccerKnowledge {
  private constructor(private readonly db: LoadedData) {}

  static load(dataDir: string): SoccerKnowledge {
    return new SoccerKnowledge(loadData(dataDir));
  }

  // ------------------------------------------------------------ helpers

  private name(key: string): string {
    return this.db.teams.displayName(key);
  }

  private team(query: string): string {
    const key = this.db.teams.resolve(query);
    if (key) return key;
    const suggestions = this.db.teams.suggestionsFor(query);
    throw new QueryError(
      `No team found matching "${query}".${suggestions.length ? ` Did you mean: ${suggestions.join(', ')}?` : ''}`,
      { error: 'team_not_found', query, suggestions },
    );
  }

  private competition(text: string | undefined): Competition | undefined {
    if (text === undefined || text.trim() === '' || fold(text) === 'all') return undefined;
    const competition = parseCompetition(text);
    if (!competition) {
      throw new QueryError(`Unknown competition "${text}". Known competitions: ${COMPETITIONS.join(', ')}.`, {
        error: 'competition_not_found', query: text, competitions: [...COMPETITIONS],
      });
    }
    return competition;
  }

  private matchView(m: Match): Record<string, unknown> {
    return {
      date: m.date,
      time: m.time,
      competition: m.competition,
      season: m.season,
      round: m.round,
      stage: m.stage,
      home: this.name(m.home),
      away: this.name(m.away),
      homeGoals: m.homeGoals,
      awayGoals: m.awayGoals,
      arena: m.arena,
      stats: m.stats,
      derby: derbyName(m.home, m.away),
      sources: m.sources,
    };
  }

  private matchLine(m: Match): string {
    const detail = m.round !== undefined ? `${m.competition} Round ${m.round}` : m.stage ? `${m.competition} ${m.stage}` : `${m.competition} ${m.season}`;
    const extras: string[] = [];
    if (m.stats?.corners) extras.push(`corners ${m.stats.corners.home}-${m.stats.corners.away}`);
    if (m.stats?.shots) extras.push(`shots ${m.stats.shots.home}-${m.stats.shots.away}`);
    return `${m.date}: ${this.name(m.home)} ${m.homeGoals}-${m.awayGoals} ${this.name(m.away)} (${detail})${extras.length ? ` [${extras.join(', ')}]` : ''}`;
  }

  private matchList(matches: Match[], limit: number): string {
    const lines = matches.slice(0, limit).map((m) => `- ${this.matchLine(m)}`);
    if (matches.length > limit) lines.push(`- ... (${matches.length - limit} more matches in dataset)`);
    return lines.join('\n');
  }

  private recordView(r: TeamRecord): Record<string, unknown> {
    return { ...r, team: this.name(r.team) };
  }

  private recordText(r: TeamRecord): string {
    return [
      `- Matches: ${r.played}`,
      `- Wins: ${r.won}, Draws: ${r.drawn}, Losses: ${r.lost}`,
      `- Goals For: ${r.goalsFor}, Goals Against: ${r.goalsAgainst} (GD ${r.goalDifference >= 0 ? '+' : ''}${r.goalDifference})`,
      `- Points: ${r.points}`,
      `- Win rate: ${pct(r.winRate)}`,
    ].join('\n');
  }

  private filter(q: { competition?: Competition; season?: number; from?: string; to?: string }): Match[] {
    return this.db.matches.filter((m) =>
      (!q.competition || m.competition === q.competition) &&
      (q.season === undefined || m.season === q.season) &&
      (!q.from || m.date >= q.from) &&
      (!q.to || m.date <= q.to));
  }

  /**
   * A league season's matches, without stray records of teams that barely
   * appear (e.g. a regional match mislabelled as Serie A in one dataset).
   */
  private leagueMatches(competition: Competition, season: number): { matches: Match[]; stray: Match[] } {
    const all = this.filter({ competition, season });
    const appearances = new Map<string, number>();
    for (const m of all) for (const t of [m.home, m.away]) appearances.set(t, (appearances.get(t) ?? 0) + 1);
    const counts = [...appearances.values()].sort((a, b) => a - b);
    const median = counts.length ? counts[Math.floor(counts.length / 2)] : 0;
    const regular = (t: string) => (appearances.get(t) ?? 0) >= median * 0.25;
    return {
      matches: all.filter((m) => regular(m.home) && regular(m.away)),
      stray: all.filter((m) => !(regular(m.home) && regular(m.away))),
    };
  }

  private scope(competition?: Competition, season?: number): string {
    return [season, competition ?? 'all competitions'].filter((x) => x !== undefined).join(' ');
  }

  // ------------------------------------------------------------ matches

  searchMatches(q: MatchQuery): Answer {
    const team = q.team ? this.team(q.team) : undefined;
    const opponent = q.opponent ? this.team(q.opponent) : undefined;
    const competition = this.competition(q.competition);
    const from = normaliseDate(q.date_from);
    const to = normaliseDate(q.date_to);
    const venue = q.venue ?? 'all';
    const limit = q.limit ?? 50;

    const found = this.filter({ competition, season: q.season, from, to })
      .filter((m) => {
        if (team) {
          const isHome = m.home === team;
          const isAway = m.away === team;
          if (venue === 'home' && !isHome) return false;
          if (venue === 'away' && !isAway) return false;
          if (!isHome && !isAway) return false;
          if (opponent && !(isHome ? m.away === opponent : m.home === opponent)) return false;
        } else if (opponent && m.home !== opponent && m.away !== opponent) {
          return false;
        }
        return true;
      })
      .sort(byDateDesc);

    const title = team && opponent
      ? `${this.name(team)} vs ${this.name(opponent)}`
      : team ? `${this.name(team)} matches` : 'Matches';
    const filters = [
      venue !== 'all' && team ? `${venue} only` : '',
      competition ?? '',
      q.season !== undefined ? `season ${q.season}` : '',
      from || to ? `${from ?? '…'} to ${to ?? '…'}` : '',
    ].filter(Boolean);
    const lines = [`${title}${filters.length ? ` (${filters.join(', ')})` : ''}: ${found.length} found`];
    if (found.length) lines.push(this.matchList(found, limit));

    const data: Record<string, unknown> = {
      team: team && this.name(team),
      opponent: opponent && this.name(opponent),
      total: found.length,
      matches: found.slice(0, limit).map((m) => this.matchView(m)),
    };
    if (team && opponent) {
      const h2h = headToHead(team, opponent, found);
      data.headToHead = h2h;
      lines.push('', `Head-to-head in dataset: ${this.name(team)} ${h2h.teamWins} wins, ${this.name(opponent)} ${h2h.opponentWins} wins, ${h2h.draws} draws`);
    }
    return { text: lines.join('\n'), data };
  }

  cupFinals(q: { competition?: string; season?: number }): Answer {
    const competition = this.competition(q.competition) ?? 'Copa do Brasil';
    if (LEAGUES.has(competition)) {
      throw new QueryError(`${competition} is a league and has no finals — ask for its standings instead.`, { error: 'not_a_cup', competition });
    }
    const seasons = [...new Set(this.filter({ competition, season: q.season }).map((m) => m.season))].sort((a, b) => b - a);
    const finals = seasons.flatMap((season) => {
      const final = this.finalOf(competition, season);
      return final ? [final] : [];
    });
    const lines = [`${competition} finals in dataset: ${finals.length}`];
    for (const f of finals) {
      const outcome = f.winner
        ? `${f.winner} beat ${f.runnerUp} ${f.winnerGoals}-${f.runnerUpGoals}${f.legs.length > 1 ? ' on aggregate' : ''}`
        : `${f.teams[0]} and ${f.teams[1]} level ${f.winnerGoals}-${f.runnerUpGoals} on aggregate (decided on penalties — not recorded in the data)`;
      lines.push(`${f.season}: ${outcome}${f.inferred ? ' (final inferred as the last tie of the season)' : ''}`);
      for (const leg of f.legMatches) lines.push(`  - ${this.matchLine(leg)}`);
    }
    return {
      text: lines.join('\n'),
      data: { competition, finals: finals.map(({ legMatches: _, ...f }) => f) },
    };
  }

  private finalOf(competition: Competition, season: number) {
    const matches = this.filter({ competition, season }).sort((a, b) => a.date.localeCompare(b.date));
    let legs = matches.filter((m) => m.stage === 'final');
    let inferred = false;
    if (!legs.length) {
      const rounds = matches.filter((m) => m.round !== undefined);
      const last = Math.max(...rounds.map((m) => m.round!));
      const candidate = rounds.filter((m) => m.round === last);
      if (candidate.length && new Set(candidate.flatMap((m) => [m.home, m.away])).size === 2) legs = candidate;
    }
    if (!legs.length && matches.length) {
      const last = matches[matches.length - 1];
      const previous = matches[matches.length - 2];
      legs = previous && previous.home === last.away && previous.away === last.home ? [previous, last] : [last];
      inferred = true;
    }
    if (!legs.length) return undefined;
    const [a, b] = [legs[0].home, legs[0].away];
    const goals = (team: string) => legs.reduce((sum, m) => sum + (m.home === team ? m.homeGoals : m.away === team ? m.awayGoals : 0), 0);
    const [ga, gb] = [goals(a), goals(b)];
    const winner = ga > gb ? a : gb > ga ? b : undefined;
    const runnerUp = winner === a ? b : winner === b ? a : undefined;
    return {
      season,
      teams: [this.name(a), this.name(b)],
      winner: winner && this.name(winner),
      runnerUp: runnerUp && this.name(runnerUp),
      winnerGoals: Math.max(ga, gb),
      runnerUpGoals: Math.min(ga, gb),
      level: ga === gb,
      inferred,
      legs: legs.map((m) => this.matchView(m)),
      legMatches: legs,
    };
  }

  findDerbies(q: { season?: number; competition?: string; team?: string; limit?: number }): Answer {
    const competition = this.competition(q.competition);
    const team = q.team ? this.team(q.team) : undefined;
    const limit = q.limit ?? 100;
    const derbies = this.filter({ competition, season: q.season })
      .filter((m) => derbyName(m.home, m.away) && (!team || m.home === team || m.away === team))
      .sort(byDateDesc);
    const lines = [`Derbies (${this.scope(competition, q.season)}): ${derbies.length} found`];
    lines.push(...derbies.slice(0, limit).map((m) => `- ${this.matchLine(m)} — ${derbyName(m.home, m.away)}`));
    if (derbies.length > limit) lines.push(`- ... (${derbies.length - limit} more)`);
    return { text: lines.join('\n'), data: { total: derbies.length, matches: derbies.slice(0, limit).map((m) => this.matchView(m)) } };
  }

  biggestWins(q: { competition?: string; season?: number; team?: string; limit?: number }): Answer {
    const competition = this.competition(q.competition);
    const team = q.team ? this.team(q.team) : undefined;
    const limit = q.limit ?? 10;
    const wins = this.filter({ competition, season: q.season })
      .filter((m) => m.homeGoals !== m.awayGoals && (!team || m.home === team || m.away === team))
      .sort((a, b) =>
        Math.abs(b.homeGoals - b.awayGoals) - Math.abs(a.homeGoals - a.awayGoals) ||
        Math.max(b.homeGoals, b.awayGoals) - Math.max(a.homeGoals, a.awayGoals) ||
        byDateDesc(a, b))
      .slice(0, limit);
    const lines = [`Biggest wins (${this.scope(competition, q.season)}${team ? `, involving ${this.name(team)}` : ''}):`];
    wins.forEach((m, i) => lines.push(`${i + 1}. ${this.matchLine(m)} — margin ${Math.abs(m.homeGoals - m.awayGoals)}`));
    return {
      text: lines.join('\n'),
      data: { matches: wins.map((m) => ({ ...this.matchView(m), margin: Math.abs(m.homeGoals - m.awayGoals) })) },
    };
  }

  // -------------------------------------------------------------- teams

  teamRecord(q: { team: string; season?: number; competition?: string; venue?: Venue }): Answer {
    const team = this.team(q.team);
    const competition = this.competition(q.competition);
    const venue = q.venue ?? 'all';
    const record = recordFor(team, this.filter({ competition, season: q.season }), venue);
    const heading = `${this.name(team)} ${venue === 'all' ? 'overall' : venue} record (${this.scope(competition, q.season)}):`;
    return {
      text: `${heading}\n${this.recordText(record)}`,
      data: { ...this.recordView(record), venue, season: q.season, competition: competition ?? 'all' },
    };
  }

  headToHead(q: { team: string; opponent: string; competition?: string; season?: number }): Answer {
    const team = this.team(q.team);
    const opponent = this.team(q.opponent);
    const competition = this.competition(q.competition);
    const meetings = this.filter({ competition, season: q.season })
      .filter((m) => (m.home === team && m.away === opponent) || (m.home === opponent && m.away === team))
      .sort(byDateDesc);
    const h2h = headToHead(team, opponent, meetings);
    const [t, o] = [this.name(team), this.name(opponent)];
    const lines = [
      `${t} vs ${o} head-to-head (${this.scope(competition, q.season)}):`,
      `- Matches: ${h2h.played}`,
      `- ${t} wins: ${h2h.teamWins}, ${o} wins: ${h2h.opponentWins}, Draws: ${h2h.draws}`,
      `- Goals: ${t} ${h2h.teamGoals}, ${o} ${h2h.opponentGoals}`,
    ];
    if (meetings.length) lines.push('Recent meetings:', this.matchList(meetings, 10));
    return { text: lines.join('\n'), data: { team: t, opponent: o, ...h2h, matches: meetings.slice(0, 10).map((m) => this.matchView(m)) } };
  }

  teamCompetitions(q: { team: string }): Answer {
    const team = this.team(q.team);
    const competitions = COMPETITIONS.flatMap((competition) => {
      const matches = this.filter({ competition }).filter((m) => m.home === team || m.away === team);
      if (!matches.length) return [];
      const seasons = [...new Set(matches.map((m) => m.season))].sort((a, b) => a - b);
      const { team: _, ...record } = recordFor(team, matches);
      return [{ competition, ...record, seasons }];
    });
    const lines = [`Competitions ${this.name(team)} has played in (dataset):`];
    for (const c of competitions) {
      lines.push(`- ${c.competition}: ${c.played} matches (${c.won}W, ${c.drawn}D, ${c.lost}L), goals ${c.goalsFor}-${c.goalsAgainst}, seasons ${c.seasons[0]}–${c.seasons[c.seasons.length - 1]}`);
    }
    return { text: lines.join('\n'), data: { team: this.name(team), competitions } };
  }

  teamRankings(q: { metric?: string; venue?: Venue; season?: number; competition?: string; minMatches?: number; limit?: number }): Answer {
    const metric = q.metric ?? 'win_rate';
    const venue = q.venue ?? 'all';
    const competition = this.competition(q.competition);
    const records = recordsFor(this.filter({ competition, season: q.season }), venue);
    const most = Math.max(0, ...records.map((r) => r.played));
    const minMatches = q.minMatches ?? Math.max(1, Math.ceil(most * 0.25));
    const sorters: Record<string, (a: TeamRecord, b: TeamRecord) => number> = {
      win_rate: (a, b) => b.winRate - a.winRate || b.points / b.played - a.points / a.played || b.goalDifference - a.goalDifference || b.played - a.played,
      goals_for: (a, b) => b.goalsFor - a.goalsFor || a.played - b.played,
      goals_against: (a, b) => a.goalsAgainst / a.played - b.goalsAgainst / b.played,
      points: (a, b) => b.points - a.points || b.goalDifference - a.goalDifference,
      goal_difference: (a, b) => b.goalDifference - a.goalDifference || b.goalsFor - a.goalsFor,
      wins: (a, b) => b.won - a.won || a.played - b.played,
    };
    const sorter = sorters[metric];
    if (!sorter) throw new QueryError(`Unknown ranking "${metric}". Use one of: ${Object.keys(sorters).join(', ')}.`, { error: 'unknown_metric', metric });
    const limit = q.limit ?? 10;
    const ranked = records.filter((r) => r.played >= minMatches).sort((a, b) => sorter(a, b) || this.name(a.team).localeCompare(this.name(b.team)));
    const label: Record<string, string> = {
      win_rate: 'win rate', goals_for: 'goals scored', goals_against: 'fewest goals conceded per match', points: 'points',
      goal_difference: 'goal difference', wins: 'wins',
    };
    const lines = [`Teams ranked by ${label[metric]}${venue !== 'all' ? ` (${venue} matches)` : ''} — ${this.scope(competition, q.season)}, min ${minMatches} matches:`];
    ranked.slice(0, limit).forEach((r, i) => {
      lines.push(`${i + 1}. ${this.name(r.team)} - ${r.played} matches, ${r.won}W ${r.drawn}D ${r.lost}L, goals ${r.goalsFor}-${r.goalsAgainst}, win rate ${pct(r.winRate)}`);
    });
    return {
      text: lines.join('\n'),
      data: { metric, venue, season: q.season, competition: competition ?? 'all', minMatches, rankings: ranked.slice(0, limit).map((r) => this.recordView(r)) },
    };
  }

  teamProfile(q: { team: string }): Answer {
    const team = this.team(q.team);
    const matches = this.db.matches.filter((m) => m.home === team || m.away === team).sort(byDateDesc);
    const record = recordFor(team, matches);
    const competitions = this.teamCompetitions({ team: q.team }).data.competitions as { competition: string; played: number }[];
    const squad = this.db.players.filter((p) => p.clubKey === team).sort((a, b) => b.overall - a.overall || a.name.localeCompare(b.name));
    const averageRating = squad.length ? round(squad.reduce((s, p) => s + p.overall, 0) / squad.length, 1) : undefined;
    const seasons = [...new Set(matches.map((m) => m.season))].sort((a, b) => a - b);
    const name = this.name(team);
    const lines = [
      `${name} — team profile`,
      `Results in dataset (${seasons.length ? `${seasons[0]}–${seasons[seasons.length - 1]}` : 'none'}):`,
      this.recordText(record),
      `Competitions: ${competitions.map((c) => `${c.competition} (${c.played})`).join(', ') || 'none'}`,
    ];
    if (matches.length) lines.push('Recent matches:', this.matchList(matches, 5));
    lines.push(squad.length
      ? `FIFA squad: ${squad.length} players, average rating ${averageRating}. Top players:`
      : 'FIFA squad: no players listed for this club in the FIFA data.');
    squad.slice(0, 10).forEach((p, i) => lines.push(`${i + 1}. ${p.name} - Overall: ${p.overall}, Position: ${p.position}, Nationality: ${p.nationality}`));
    return {
      text: lines.join('\n'),
      data: {
        team: name,
        record: this.recordView(record),
        competitions,
        seasons,
        recentMatches: matches.slice(0, 5).map((m) => this.matchView(m)),
        squad: { size: squad.length, averageRating, players: squad.slice(0, 10).map((p) => this.playerView(p)) },
      },
    };
  }

  // -------------------------------------------------------- competitions

  standings(q: { competition?: string; season: number }): Answer {
    const competition = this.competition(q.competition) ?? 'Brasileirão';
    if (!LEAGUES.has(competition)) {
      throw new QueryError(`${competition} is a knockout competition — ask for its bracket or finals instead.`, { error: 'not_a_league', competition });
    }
    const { matches, stray } = this.leagueMatches(competition, q.season);
    if (!matches.length) {
      const seasons = [...new Set(this.filter({ competition }).map((m) => m.season))].sort((a, b) => a - b);
      throw new QueryError(`No ${competition} matches recorded for ${q.season}. Seasons available: ${seasons.join(', ')}.`, {
        error: 'season_not_found', competition, season: q.season, seasons,
      });
    }
    const table = leagueTable(matches, (k) => this.name(k));
    const { complete, missingMatches } = completeness(table.length, matches.length);
    const relegatedCount = !complete || competition === 'Serie C' || table.length < 8 ? 0 : q.season === 2003 ? 2 : 4;
    const relegated = relegatedCount ? table.slice(-relegatedCount).map((r) => this.name(r.team)) : [];
    const leader = this.name(table[0].team);
    const champion = complete ? leader : undefined;
    const lines = [`${q.season} ${competition} ${complete ? 'Final' : 'Provisional'} Standings (calculated from ${matches.length} matches):`];
    if (!complete) {
      lines.push(`Warning: the data is missing ${missingMatches} of this season's ${matches.length + missingMatches} matches, so no champion or relegation is given. ${leader} lead the table.`);
    }
    for (const r of table) {
      const note = r.position === 1 && complete ? ' - Champion' : relegated.includes(this.name(r.team)) ? ' - Relegated' : '';
      lines.push(`${r.position}. ${this.name(r.team)} - ${r.points} pts (${r.won}W, ${r.drawn}D, ${r.lost}L) GD ${r.goalDifference >= 0 ? '+' : ''}${r.goalDifference}${note}`);
    }
    if (relegated.length) lines.push('', `Relegated: ${relegated.join(', ')}`);
    if (stray.length) lines.push('', `Ignored ${stray.length} stray match(es) involving teams that otherwise do not appear in this season: ${stray.map((m) => this.matchLine(m)).join('; ')}`);
    lines.push('', 'Note: calculated from match results only; official tables may differ (e.g. points deductions).');
    return {
      text: lines.join('\n'),
      data: { competition, season: q.season, matches: matches.length, strayMatches: stray.length, complete, missingMatches, champion, leader, relegated, table: table.map((r) => ({ ...this.recordView(r), position: r.position })) },
    };
  }

  knockoutBracket(q: { competition?: string; season: number }): Answer {
    const competition = this.competition(q.competition) ?? 'Libertadores';
    if (LEAGUES.has(competition)) {
      throw new QueryError(`${competition} is a league — ask for its standings instead.`, { error: 'not_a_cup', competition });
    }
    const matches = this.filter({ competition, season: q.season }).sort((a, b) => a.date.localeCompare(b.date));
    const stageOf = (m: Match) => (m.stage ? m.stage : m.round !== undefined ? `round ${m.round}` : undefined);
    const stageNames = [...new Set(matches.map(stageOf).filter((s): s is string => !!s && s !== 'group stage'))].sort((a, b) => {
      const ia = KNOCKOUT_ORDER.indexOf(a);
      const ib = KNOCKOUT_ORDER.indexOf(b);
      return ia !== -1 && ib !== -1 ? ia - ib : a.localeCompare(b, undefined, { numeric: true });
    });
    const stages = stageNames.map((stage) => {
      const ties = new Map<string, Match[]>();
      for (const m of matches.filter((x) => stageOf(x) === stage)) {
        const key = [m.home, m.away].sort().join(' v ');
        ties.set(key, [...(ties.get(key) ?? []), m]);
      }
      return {
        stage,
        ties: [...ties.values()].map((legs) => {
          const [a, b] = [legs[0].home, legs[0].away];
          const goals = (t: string) => legs.reduce((s, m) => s + (m.home === t ? m.homeGoals : m.awayGoals), 0);
          const [ga, gb] = [goals(a), goals(b)];
          const winner = ga > gb ? a : gb > ga ? b : undefined;
          return {
            teams: [this.name(a), this.name(b)],
            winner: winner && this.name(winner),
            loser: winner && this.name(winner === a ? b : a),
            winnerGoals: Math.max(ga, gb),
            loserGoals: Math.min(ga, gb),
            level: ga === gb,
            legs: legs.map((m) => this.matchView(m)),
          };
        }),
      };
    });
    const lines = [`${q.season} ${competition} knockout bracket:`];
    for (const s of stages) {
      lines.push('', `${s.stage[0].toUpperCase()}${s.stage.slice(1)}:`);
      for (const t of s.ties) {
        lines.push(t.winner
          ? `- ${t.winner} beat ${t.loser} ${t.winnerGoals}-${t.loserGoals}${t.legs.length > 1 ? ' on aggregate' : ''}`
          : `- ${t.teams[0]} ${t.winnerGoals}-${t.loserGoals} ${t.teams[1]} (level on aggregate — tiebreak not recorded)`);
      }
    }
    if (!stages.length) lines.push('No knockout matches recorded for this season.');
    return { text: lines.join('\n'), data: { competition, season: q.season, stages } };
  }

  // ---------------------------------------------------------- statistics

  competitionStats(q: { competition?: string; season?: number }): Answer {
    const competition = this.competition(q.competition);
    const summary = summarise(this.filter({ competition, season: q.season }));
    const text = [
      `Match statistics (${this.scope(competition, q.season)}):`,
      `- Matches: ${summary.matches}`,
      `- Goals: ${summary.goals}`,
      `- Average goals per match: ${summary.averageGoals.toFixed(2)}`,
      `- Home win rate: ${pct(summary.homeWinRate)} (${summary.homeWins})`,
      `- Draw rate: ${pct(summary.drawRate)} (${summary.draws})`,
      `- Away win rate: ${pct(summary.awayWinRate)} (${summary.awayWins})`,
    ].join('\n');
    return { text, data: { competition: competition ?? 'all', season: q.season, ...summary } };
  }

  compareSeasons(q: { seasons: number[]; competition?: string }): Answer {
    const competition = this.competition(q.competition) ?? 'Brasileirão';
    const seasons = q.seasons.map((season) => {
      const matches = LEAGUES.has(competition) ? this.leagueMatches(competition, season).matches : this.filter({ competition, season });
      const summary = summarise(matches);
      const table = matches.length && LEAGUES.has(competition) ? leagueTable(matches, (k) => this.name(k)) : [];
      const { complete } = completeness(table.length, matches.length);
      const topScorer = recordsFor(matches).sort((a, b) => b.goalsFor - a.goalsFor)[0];
      return {
        season,
        ...summary,
        teams: new Set(matches.flatMap((m) => [m.home, m.away])).size,
        complete: table.length ? complete : undefined,
        champion: table[0] && complete ? this.name(table[0].team) : undefined,
        leader: table[0] ? this.name(table[0].team) : undefined,
        championPoints: table[0]?.points,
        topScoringTeam: topScorer ? this.name(topScorer.team) : undefined,
        topScoringTeamGoals: topScorer?.goalsFor,
      };
    });
    const lines = [`${competition} season comparison:`];
    for (const s of seasons) {
      lines.push(
        `${s.season}: ${s.matches} matches, ${s.goals} goals (${s.averageGoals.toFixed(2)} per match), home wins ${pct(s.homeWinRate)}, draws ${pct(s.drawRate)}, away wins ${pct(s.awayWinRate)}` +
        `${s.champion ? `; champion ${s.champion} (${s.championPoints} pts)` : s.leader ? `; leader ${s.leader} (${s.championPoints} pts, season incomplete in data)` : ''}${s.topScoringTeam ? `; most goals ${s.topScoringTeam} (${s.topScoringTeamGoals})` : ''}`,
      );
    }
    return { text: lines.join('\n'), data: { competition, seasons } };
  }

  // -------------------------------------------------------------- players

  private playerView(p: Player): Record<string, unknown> {
    const { clubKey: _, ...view } = p;
    return view;
  }

  private playerLine(p: Player): string {
    return `${p.name} - Overall: ${p.overall}, Position: ${p.position || '?'}, Club: ${p.club || 'none'}, Nationality: ${p.nationality}, Age: ${p.age ?? '?'}`;
  }

  private nationality(text: string): string {
    const folded = fold(text);
    return DEMONYMS[folded] ?? folded;
  }

  searchPlayers(q: { name?: string; nationality?: string; club?: string; position?: string; minOverall?: number; limit?: number }): Answer {
    let players = this.db.players;
    if (q.name) {
      const wanted = tokens(q.name);
      players = players.filter((p) => {
        const have = tokens(p.name);
        return wanted.every((w) => have.some((h) => h.startsWith(w)));
      });
    }
    if (q.nationality) {
      const nationality = this.nationality(q.nationality);
      players = players.filter((p) => fold(p.nationality) === nationality);
    }
    if (q.club) {
      const key = this.db.teams.resolve(q.club) ?? this.db.teams.keyFor(parseTeamName(q.club), true);
      const byKey = players.filter((p) => p.clubKey === key);
      const folded = fold(q.club);
      players = byKey.length ? byKey : players.filter((p) => fold(p.club).includes(folded));
    }
    if (q.position) {
      const positions = positionsFor(q.position);
      players = players.filter((p) => positions.includes(p.position));
    }
    if (q.minOverall !== undefined) players = players.filter((p) => p.overall >= q.minOverall!);
    const sorted = [...players].sort((a, b) => b.overall - a.overall || (b.potential ?? 0) - (a.potential ?? 0) || a.name.localeCompare(b.name));
    const limit = q.limit ?? 25;
    const criteria = [q.name && `name "${q.name}"`, q.nationality && `nationality ${q.nationality}`, q.club && `club ${q.club}`, q.position && `position ${q.position}`, q.minOverall !== undefined && `overall ≥ ${q.minOverall}`]
      .filter(Boolean).join(', ');
    const lines = [`Players matching ${criteria || 'all'}: ${sorted.length} found${sorted.length > limit ? ` (top ${limit} by rating shown)` : ''}`];
    sorted.slice(0, limit).forEach((p, i) => lines.push(`${i + 1}. ${this.playerLine(p)}`));
    if (sorted.length) {
      const avg = round(sorted.reduce((s, p) => s + p.overall, 0) / sorted.length, 1);
      lines.push('', `Average rating of all ${sorted.length}: ${avg}`);
    }
    return { text: lines.join('\n'), data: { total: sorted.length, players: sorted.slice(0, limit).map((p) => this.playerView(p)) } };
  }

  getPlayer(q: { name: string }): Answer {
    const folded = fold(q.name);
    const exact = this.db.players.filter((p) => fold(p.name) === folded);
    const wanted = tokens(q.name);
    const partial = exact.length
      ? exact
      : this.db.players.filter((p) => {
        const have = tokens(p.name);
        return wanted.length > 0 && wanted.every((w) => have.some((h) => h.startsWith(w)));
      });
    const ranked = [...partial].sort((a, b) => b.overall - a.overall);
    if (!ranked.length) {
      const words = wanted.filter((w) => w.length >= 3);
      const suggestions = this.db.players
        .map((p) => ({ p, shared: tokens(p.name).filter((t) => words.includes(t)).length }))
        .filter((x) => x.shared > 0)
        .sort((a, b) => b.shared - a.shared || b.p.overall - a.p.overall)
        .slice(0, 5)
        .map((x) => x.p.name);
      return {
        text: `No player named "${q.name}" in the FIFA dataset.${suggestions.length ? ` Similar names: ${suggestions.join(', ')}.` : ''}`,
        data: { found: false, query: q.name, suggestions },
      };
    }
    const [player, ...others] = ranked;
    const skills = Object.entries(player.skills).sort((a, b) => b[1] - a[1]);
    const lines = [
      `${player.name}`,
      `- Club: ${player.club || 'none'}${player.jerseyNumber !== undefined ? ` (#${player.jerseyNumber})` : ''}`,
      `- Nationality: ${player.nationality}, Age: ${player.age ?? '?'}`,
      `- Position: ${player.position || '?'}, Preferred foot: ${player.preferredFoot ?? '?'}`,
      `- Overall: ${player.overall}, Potential: ${player.potential ?? '?'}`,
      `- Height: ${player.height ?? '?'}, Weight: ${player.weight ?? '?'}, Value: ${player.value ?? '?'}, Wage: ${player.wage ?? '?'}`,
      `- Best attributes: ${skills.slice(0, 6).map(([k, v]) => `${k} ${v}`).join(', ')}`,
    ];
    if (others.length) lines.push(`Other players matching "${q.name}": ${others.slice(0, 5).map((p) => `${p.name} (${p.club})`).join(', ')}`);
    return { text: lines.join('\n'), data: { found: true, player: this.playerView(player), otherMatches: others.slice(0, 5).map((p) => this.playerView(p)) } };
  }

  brazilianClubSquads(q: { nationality?: string }): Answer {
    const nationality = q.nationality ? this.nationality(q.nationality) : undefined;
    const brazilianClubs = new Set(
      this.db.matches
        .filter((m) => DOMESTIC.has(m.competition))
        .flatMap((m) => [m.home, m.away])
        .filter((key) => BRAZILIAN_STATES.has(key.split('|')[1])),
    );
    const groups = new Map<string, Player[]>();
    for (const p of this.db.players) {
      if (!p.clubKey || !brazilianClubs.has(p.clubKey)) continue;
      if (nationality && fold(p.nationality) !== nationality) continue;
      groups.set(p.club, [...(groups.get(p.club) ?? []), p]);
    }
    const clubs = [...groups.entries()]
      .map(([club, players]) => {
        const sorted = players.sort((a, b) => b.overall - a.overall);
        return {
          club,
          team: this.name(players[0].clubKey!),
          players: players.length,
          averageRating: round(players.reduce((s, p) => s + p.overall, 0) / players.length, 1),
          bestPlayer: sorted[0].name,
          bestRating: sorted[0].overall,
        };
      })
      .sort((a, b) => b.players - a.players || b.averageRating - a.averageRating || a.club.localeCompare(b.club));
    const who = q.nationality ? `${q.nationality} players` : 'Players';
    const lines = [`${who} at Brazilian clubs (FIFA data, clubs matched to Brazilian match data):`];
    for (const c of clubs) lines.push(`- ${c.club}: ${c.players} players (avg rating: ${c.averageRating}), best: ${c.bestPlayer} (${c.bestRating})`);
    if (!clubs.length) lines.push('- none found');
    return { text: lines.join('\n'), data: { nationality: q.nationality, clubs } };
  }

  // ------------------------------------------------------------- datasets

  datasetInfo(): Answer {
    const lines = ['Datasets loaded:'];
    for (const d of this.db.datasets) lines.push(`- ${d.name} (${d.file}): ${d.records} records, ${d.usable} usable — ${d.description}`);
    const seasons = (c: Competition) => {
      const s = [...new Set(this.filter({ competition: c }).map((m) => m.season))].sort((a, b) => a - b);
      return s.length ? `${s[0]}–${s[s.length - 1]}` : 'none';
    };
    lines.push('', `Distinct matches after merging duplicates across datasets: ${this.db.matches.length}`);
    for (const c of COMPETITIONS) lines.push(`- ${c}: ${this.filter({ competition: c }).length} matches, seasons ${seasons(c)}`);
    lines.push(`Teams: ${this.db.teams.allKeys().length}, Players: ${this.db.players.length}`);
    return {
      text: lines.join('\n'),
      data: {
        datasets: this.db.datasets,
        totals: { matches: this.db.matches.length, teams: this.db.teams.allKeys().length, players: this.db.players.length },
        competitions: COMPETITIONS.map((c) => ({ competition: c, matches: this.filter({ competition: c }).length, seasons: seasons(c) })),
      },
    };
  }
}
