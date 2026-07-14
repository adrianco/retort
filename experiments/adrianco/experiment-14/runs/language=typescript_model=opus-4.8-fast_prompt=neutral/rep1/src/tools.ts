/**
 * Brazilian Soccer MCP — Tool definitions & dispatch
 * --------------------------------------------------
 * Context: Declares the MCP tools exposed to the LLM and maps each tool call to
 * a `SoccerStore` query plus a `format.ts` renderer. The `callTool` dispatcher
 * is deliberately decoupled from the MCP transport so the entire tool surface
 * can be exercised in unit tests by calling `callTool(store, name, args)`
 * directly. `server.ts` is a thin adapter that forwards protocol requests here.
 */

import type { SoccerStore } from "./store.js";
import {
  formatCompetitionStats,
  formatHeadToHead,
  formatMatches,
  formatPlayers,
  formatStandings,
  formatTeamRecord,
} from "./format.js";

export interface ToolDef {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
}

const str = (description: string) => ({ type: "string", description });
const int = (description: string) => ({ type: "integer", description });

export const TOOL_DEFS: ToolDef[] = [
  {
    name: "find_matches",
    description:
      "Search match results across all Brazilian competitions (Brasileirão Série A/B/C, " +
      "Copa do Brasil, Copa Libertadores). Filter by team, opponent, competition, season, " +
      "date range, and home/away venue. Team names are matched flexibly (accents and state " +
      "suffixes like '-SP' are ignored).",
    inputSchema: {
      type: "object",
      properties: {
        team: str("Team name (e.g. 'Flamengo', 'São Paulo', 'Palmeiras-SP')."),
        opponent: str("Optional opponent team to find matches between two specific teams."),
        competition: str(
          "Competition filter, substring match (e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores').",
        ),
        season: int("Season / year, e.g. 2019."),
        venue: { type: "string", enum: ["home", "away", "either"], description: "Restrict `team` to home or away matches." },
        startDate: str("Inclusive ISO start date YYYY-MM-DD."),
        endDate: str("Inclusive ISO end date YYYY-MM-DD."),
        limit: int("Max matches to list (default 25)."),
      },
    },
  },
  {
    name: "head_to_head",
    description:
      "Compare two teams head-to-head across all competitions: total meetings, wins for each " +
      "side, draws, goals, and the most recent matches. Useful for derbies and rivalries.",
    inputSchema: {
      type: "object",
      properties: {
        teamA: str("First team."),
        teamB: str("Second team."),
        competition: str("Optional competition filter."),
        season: int("Optional season filter."),
      },
      required: ["teamA", "teamB"],
    },
  },
  {
    name: "team_record",
    description:
      "Aggregate a single team's record (played, wins, draws, losses, goals for/against, points, " +
      "win rate). Optionally restrict by season, competition, and home/away venue.",
    inputSchema: {
      type: "object",
      properties: {
        team: str("Team name."),
        season: int("Optional season / year."),
        competition: str("Optional competition filter."),
        venue: { type: "string", enum: ["home", "away", "either"], description: "Home-only, away-only, or both (default)." },
      },
      required: ["team"],
    },
  },
  {
    name: "league_standings",
    description:
      "Compute a league table for a competition + season directly from match results " +
      "(3 pts win, 1 pt draw). Best for Brasileirão Série A/B/C. Shows rank, points, W/D/L, " +
      "goals for/against and goal difference; rank 1 is marked Champion.",
    inputSchema: {
      type: "object",
      properties: {
        competition: str("Competition (default 'Brasileirão Série A')."),
        season: int("Season / year, e.g. 2019."),
        limit: int("Max rows (default 30)."),
      },
      required: ["season"],
    },
  },
  {
    name: "competition_stats",
    description:
      "Aggregate statistics for a competition/scope: total & average goals per match, home/away " +
      "win rates, draws, and the biggest-margin victories. Filter by competition, season, team.",
    inputSchema: {
      type: "object",
      properties: {
        competition: str("Optional competition filter."),
        season: int("Optional season."),
        team: str("Optional team filter (stats for matches involving this team)."),
      },
    },
  },
  {
    name: "search_players",
    description:
      "Search the FIFA player database by name, nationality (e.g. 'Brazil'), club, and position. " +
      "Filter by minimum overall rating and sort by overall/potential/age/name. Returns ratings " +
      "and attributes. Great for 'top Brazilian players' or 'players at <club>'.",
    inputSchema: {
      type: "object",
      properties: {
        name: str("Player name substring."),
        nationality: str("Nationality, e.g. 'Brazil'."),
        club: str("Club name substring."),
        position: str("Exact position code, e.g. 'GK', 'LW', 'CDM'."),
        minOverall: int("Minimum FIFA overall rating."),
        sortBy: { type: "string", enum: ["overall", "potential", "age", "name"], description: "Sort key (default overall)." },
        limit: int("Max players to list (default 20)."),
      },
    },
  },
  {
    name: "list_competitions",
    description:
      "List the competitions available in the dataset and, for each, the seasons covered. " +
      "Use this to discover what can be queried.",
    inputSchema: { type: "object", properties: {} },
  },
];

function asInt(v: unknown): number | undefined {
  if (v === undefined || v === null || v === "") return undefined;
  const n = Number(v);
  return Number.isFinite(n) ? Math.round(n) : undefined;
}

function asStr(v: unknown): string | undefined {
  if (v === undefined || v === null) return undefined;
  const s = String(v).trim();
  return s === "" ? undefined : s;
}

/**
 * Execute a tool by name against the store and return a formatted text answer.
 * Throws on unknown tool names; returns a friendly message for empty results.
 */
export function callTool(store: SoccerStore, name: string, args: Record<string, unknown> = {}): string {
  switch (name) {
    case "find_matches": {
      const team = asStr(args.team);
      const opponent = asStr(args.opponent);
      const competition = asStr(args.competition);
      const season = asInt(args.season);
      const limit = asInt(args.limit) ?? 25;
      const venue = (asStr(args.venue) as "home" | "away" | "either" | undefined) ?? "either";
      const matches = store.findMatches({
        team,
        opponent,
        competition,
        season,
        venue,
        startDate: asStr(args.startDate),
        endDate: asStr(args.endDate),
      });
      const parts = [
        team ? `team ${team}` : null,
        opponent ? `vs ${opponent}` : null,
        competition ?? null,
        season ? `season ${season}` : null,
        venue !== "either" && team ? `(${venue})` : null,
      ].filter(Boolean);
      const title = `Matches${parts.length ? " — " + parts.join(", ") : ""}`;
      return formatMatches(matches, title, limit);
    }

    case "head_to_head": {
      const teamA = asStr(args.teamA);
      const teamB = asStr(args.teamB);
      if (!teamA || !teamB) return "Please provide both teamA and teamB.";
      const h = store.headToHead(teamA, teamB, {
        competition: asStr(args.competition),
        season: asInt(args.season),
      });
      return formatHeadToHead(h);
    }

    case "team_record": {
      const team = asStr(args.team);
      if (!team) return "Please provide a team.";
      const season = asInt(args.season);
      const competition = asStr(args.competition);
      const venue = (asStr(args.venue) as "home" | "away" | "either" | undefined) ?? "either";
      const rec = store.teamRecord(team, { season, competition, venue });
      if (!rec) return `No team found matching "${team}".`;
      const scope = [
        competition ?? "all competitions",
        season ? `${season}` : "all seasons",
        venue !== "either" ? venue : null,
      ]
        .filter(Boolean)
        .join(", ");
      return formatTeamRecord(rec, scope);
    }

    case "league_standings": {
      const season = asInt(args.season);
      if (season === undefined) return "Please provide a season.";
      const competition = asStr(args.competition) ?? "Brasileirão Série A";
      const limit = asInt(args.limit) ?? 30;
      const rows = store.standings(competition, season);
      return formatStandings(rows, `${competition} ${season} — Final Standings (computed from matches)`, limit);
    }

    case "competition_stats": {
      const competition = asStr(args.competition);
      const season = asInt(args.season);
      const team = asStr(args.team);
      const stats = store.competitionStats({ competition, season, team });
      const scope = [competition ?? "All competitions", season ? `${season}` : null, team ? `team ${team}` : null]
        .filter(Boolean)
        .join(" — ");
      return formatCompetitionStats(stats, `Statistics — ${scope}`);
    }

    case "search_players": {
      const players = store.searchPlayers({
        name: asStr(args.name),
        nationality: asStr(args.nationality),
        club: asStr(args.club),
        position: asStr(args.position),
        minOverall: asInt(args.minOverall),
        sortBy: asStr(args.sortBy) as "overall" | "potential" | "age" | "name" | undefined,
        limit: asInt(args.limit) ?? 20,
      });
      const parts = [
        asStr(args.name) ? `name~${asStr(args.name)}` : null,
        asStr(args.nationality) ?? null,
        asStr(args.club) ? `club~${asStr(args.club)}` : null,
        asStr(args.position) ?? null,
      ].filter(Boolean);
      return formatPlayers(players, `Players${parts.length ? " — " + parts.join(", ") : ""}`, asInt(args.limit) ?? 20);
    }

    case "list_competitions": {
      const lines = store.listCompetitions().map((c) => {
        const seasons = store.seasonsFor(c);
        const range = seasons.length ? `${seasons[0]}–${seasons[seasons.length - 1]} (${seasons.length} seasons)` : "n/a";
        return `- ${c}: ${range}`;
      });
      return `Available competitions:\n${lines.join("\n")}\n\nTotal matches: ${store.matches.length}, teams: ${store.teamCount()}, players: ${store.players.length}`;
    }

    default:
      throw new Error(`Unknown tool: ${name}`);
  }
}
