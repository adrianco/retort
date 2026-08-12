import { normalizeText } from "./normalize.js";
import { SoccerService } from "./soccer-service.js";
import type { QueryResult, TeamRecord } from "./types.js";

function extractSeason(question: string): number | undefined {
  const match = /\b(19\d{2}|20\d{2})\b/.exec(question);
  return match ? Number(match[1]) : undefined;
}

function extractLimit(question: string): number | undefined {
  const match = /\b(?:top|first|last|show(?: me)?)\s+(\d{1,3})\b/i.exec(question);
  return match ? Number(match[1]) : undefined;
}

function result<T>(kind: string, summary: string, data: T, formatted: string, limitations?: string[]): QueryResult<T> {
  return { kind, summary, data, formatted, limitations };
}

export class NaturalLanguageQueryRouter {
  constructor(private readonly service: SoccerService) {}

  answer(question: string): QueryResult {
    const normalized = normalizeText(question);
    const season = extractSeason(question);
    const limit = extractLimit(question);
    const competitionKey = this.service.graph.findCompetitionInText(question);
    const competition = competitionKey ? this.service.graph.competitionNames.get(competitionKey) : undefined;
    const teams = this.service.graph.findTeamsInText(question);
    const teamNames = teams.map((team) => this.service.graph.displayTeam(team));

    if (/top scorer|artilheiro/.test(normalized)) {
      return result(
        "unsupported",
        "Goalscorer data is not present in the provided datasets",
        { available: false },
        "The provided files contain final team scores but no player-level goal events, so top scorers cannot be calculated reliably.",
        ["Player-level scoring events are not included in the six provided CSV files."],
      );
    }

    if (/derb|classico|classicos/.test(normalized)) return this.service.derbies(season, limit);

    if (/who is|quem e/.test(normalized)) {
      const name = question.replace(/^.*?(?:who is|quem [ée])\s+/i, "").replace(/[?.!]+$/, "").trim();
      return this.service.searchPlayers({ name, limit: limit ?? 10 });
    }

    if (/player|jogador|forward|attacker|midfielder|defender|goalkeeper/.test(normalized)) {
      const nationality = /brazilian|brasileir/.test(normalized) ? "Brazil" : undefined;
      const position = /forward|attacker|atacante/.test(normalized) ? "forward"
        : /midfielder|meio campo/.test(normalized) ? "midfielder"
          : /defender|defensor/.test(normalized) ? "defender"
            : /goalkeeper|keeper|goleiro/.test(normalized) ? "goalkeeper" : undefined;
      const minOverallMatch = /(?:overall|rated?|rating)\s*(?:of|at least|above|over|>=?)?\s*(\d{2})/i.exec(question);
      const nameMatch = /(?:named?|called)\s+([^?]+)$/i.exec(question);
      return this.service.searchPlayers({
        name: nameMatch?.[1]?.trim(),
        nationality,
        club: teamNames[0],
        position,
        minOverall: minOverallMatch ? Number(minOverallMatch[1]) : undefined,
        limit: limit ?? (/highest|best|top/.test(normalized) ? 20 : undefined),
      });
    }

    if (/standing|table|champion|who won|winner|campeao/.test(normalized) && season) {
      return this.service.standings(season, competition ?? "Brasileirão");
    }

    if (/relegat/.test(normalized) && season) {
      const standings = this.service.standings(season, competition ?? "Brasileirão");
      const relegated = standings.data.slice(-4);
      return result("relegation", `Bottom four in ${season}`, relegated, `${season} bottom four (table-derived):\n${relegated.map((entry) => `${entry.position}. ${entry.team} — ${entry.points} pts`).join("\n")}`, ["The dataset does not encode relegation rules or administrative decisions; this returns the bottom four calculated positions."]);
    }

    if (/compare/.test(normalized) && /\b(19\d{2}|20\d{2})\b.*\b(?:19\d{2}|20\d{2})\b/.test(question)) {
      const years = [...question.matchAll(/\b(19\d{2}|20\d{2})\b/g)].map((match) => Number(match[1])).slice(0, 2);
      const first = this.service.competitionStatistics({ competition, season: years[0] });
      const second = this.service.competitionStatistics({ competition, season: years[1] });
      return result("season-comparison", `Compared ${years[0]} and ${years[1]}`, { [years[0]!]: first.data, [years[1]!]: second.data }, `${first.formatted}\n\n${second.formatted}`);
    }

    if (/most goals|highest scoring|scored the most/.test(normalized) && season) {
      const standings = this.service.standings(season, competition ?? "Brasileirão");
      const ranked = [...standings.data].sort((a, b) => b.goalsFor - a.goalsFor || b.points - a.points);
      return result("most-goals", `${ranked[0]?.team ?? "No team"} scored the most goals`, ranked.slice(0, limit ?? 20), `${season} teams by goals scored\n${ranked.slice(0, limit ?? 20).map((entry, index) => `${index + 1}. ${entry.team} — ${entry.goalsFor} goals`).join("\n")}`);
    }

    if (/best (?:home|away) record/.test(normalized)) {
      return this.service.bestRecord({ competition: competition ?? "Brasileirão", season, venue: normalized.includes("away") ? "away" : "home" });
    }

    if (/average goals|goals per match|biggest (?:win|victor)|home win rate/.test(normalized)) {
      return this.service.competitionStatistics({ competition, season, limit });
    }

    if (/what competition|which competition|competitions has|team profile/.test(normalized) && teamNames[0]) {
      return this.service.teamProfile(teamNames[0], season);
    }

    if (teamNames.length >= 2 && (/compare|head to head|versus|\bvs\b|last play|last played|score/.test(normalized))) {
      return this.service.headToHead(teamNames[0]!, teamNames[1]!, { competition, season, limit: /last|score/.test(normalized) ? 1 : limit });
    }

    if (teamNames[0] && /record|stat|performance|wins|losses|goals scored|goals conceded/.test(normalized)) {
      const venue = /\bhome\b/.test(normalized) ? "home" : /\baway\b/.test(normalized) ? "away" : "either";
      return this.service.teamStatistics(teamNames[0], { competition: competition ?? (season ? "Brasileirão" : undefined), season, venue });
    }

    if (/final|bracket|chaveamento/.test(normalized) && competition) {
      return this.service.searchMatches({ competition, season, stage: "final", limit });
    }

    if (teamNames[0] || /match|game|fixture|played/.test(normalized)) {
      return this.service.searchMatches({ team: teamNames[0], opponent: teamNames[1], competition, season, limit });
    }

    if (/summary|dataset|coverage|what can/.test(normalized)) {
      const summary = this.service.graph.summary();
      return result("dataset-summary", "Brazilian soccer dataset coverage", summary, `Loaded ${summary.matches} deduplicated matches, ${summary.players} players, ${summary.teams} teams, and ${summary.competitions} competitions from all six supplied CSV files.`);
    }

    return result(
      "help",
      "Please ask about a team, player, competition, season, or statistic",
      { examples: ["Flamengo vs Fluminense", "Palmeiras matches in 2023", "2019 Brasileirão standings", "top Brazilian players", "average goals in the Brasileirão"] },
      "I could not identify a specific soccer query. Try: \"Flamengo vs Fluminense\", \"Palmeiras matches in 2023\", \"2019 Brasileirão standings\", or \"top Brazilian players\".",
    );
  }
}
