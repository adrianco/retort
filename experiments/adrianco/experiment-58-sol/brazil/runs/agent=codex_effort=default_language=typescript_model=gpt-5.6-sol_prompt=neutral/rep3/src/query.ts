import { foldText } from "./normalize.js";
import { formatMatches, formatPlayers, formatStandings, formatTeamStats } from "./format.js";
import { SoccerService } from "./service.js";

const KNOWN_TEAMS = [
  "Flamengo", "Fluminense", "Palmeiras", "Corinthians", "Santos", "São Paulo", "Vasco",
  "Botafogo", "Grêmio", "Internacional", "Cruzeiro", "Atlético Mineiro", "Athletico Paranaense",
  "Bahia", "Fortaleza", "Ceará", "Sport", "Náutico", "Vitória", "Coritiba"
];

const DERBIES: Array<[string, string, string]> = [
  ["Flamengo", "Fluminense", "Fla-Flu"], ["Flamengo", "Vasco", "Clássico dos Milhões"],
  ["Palmeiras", "Corinthians", "Derby Paulista"], ["Santos", "São Paulo", "San-São"],
  ["Grêmio", "Internacional", "Grenal"], ["Atlético Mineiro", "Cruzeiro", "Clássico Mineiro"],
  ["Bahia", "Vitória", "Ba-Vi"], ["Ceará", "Fortaleza", "Clássico-Rei"]
];

function detectYear(question: string): number | undefined {
  const match = question.match(/\b(19|20)\d{2}\b/);
  return match ? Number(match[0]) : undefined;
}

function detectCompetition(question: string): string | undefined {
  const text = foldText(question);
  if (text.includes("libertadores")) return "Copa Libertadores";
  if (text.includes("copa do brasil")) return "Copa do Brasil";
  if (text.includes("brasileir") || text.includes("serie a")) return "Brasileirão Serie A";
  return undefined;
}

function detectTeams(question: string): string[] {
  const folded = foldText(question);
  return KNOWN_TEAMS.filter((team) => folded.includes(foldText(team)));
}

function detectPosition(question: string): string | undefined {
  const text = foldText(question);
  if (/\b(forward|forwards|atacante|atacantes)\b/.test(text)) return "ST";
  if (/\b(goalkeeper|goalkeepers|goleiro|goleiros)\b/.test(text)) return "GK";
  if (/\b(defender|defenders|zagueiro|zagueiros)\b/.test(text)) return "CB";
  if (/\b(midfielder|midfielders|meia|meias)\b/.test(text)) return "CM";
  return undefined;
}

export interface QuestionAnswer {
  intent: string;
  answer: string;
  data: unknown;
  note?: string;
}

export class NaturalLanguageQuery {
  constructor(private readonly service: SoccerService) {}

  answer(question: string): QuestionAnswer {
    const text = foldText(question);
    const year = detectYear(question);
    const competition = detectCompetition(question);
    const teams = detectTeams(question);

    if (text.includes("derbies") || text.includes("classicos")) {
      const results = DERBIES.flatMap(([teamA, teamB, name]) => {
        const matches = this.service.headToHead(teamA, teamB, { season: year, limit: 200 }).results;
        return matches.map((match) => ({ ...match, derby: name }));
      }).sort((a, b) => b.date.localeCompare(a.date));
      return { intent: "derbies", answer: formatMatches(results.slice(0, 25), results.length), data: results };
    }

    if (teams.length >= 2 && (/\b(vs|versus|between|compare|head to head)\b/.test(text))) {
      const data = this.service.headToHead(teams[0]!, teams[1]!, { season: year, competition, limit: 200 });
      const answer = `${teams[0]} vs ${teams[1]}: ${data.teamAWins} ${teams[0]} wins, ${data.teamBWins} ${teams[1]} wins, ${data.draws} draws.\n${formatMatches(data.results, data.matches)}`;
      return { intent: "head_to_head", answer, data };
    }

    if (/\b(player|players|jogador|jogadores|forward|forwards|goalkeeper|highest rated|top rated)\b/.test(text)) {
      const nationality = /brazilian|brasileir/.test(text) ? "Brazil" : undefined;
      const result = this.service.searchPlayers({ nationality, club: teams[0], position: detectPosition(question), limit: 25 });
      return { intent: "player_search", answer: formatPlayers(result.items, result.total), data: result };
    }

    if (/\b(standing|standings|table|champion|won|winner|relegated)\b/.test(text) && year) {
      if (competition && !/brasileir|serie a/.test(foldText(competition))) {
        const data = this.service.competitionSummary(competition, year);
        const answer = data.champion
          ? `${data.champion} is the winner inferable from the recorded ${year} final score${data.finalMatches.length === 1 ? "" : "s"}.\n${formatMatches(data.finalMatches)}`
          : `The ${year} final result does not identify a unique winner from regulation scores alone.\n${formatMatches(data.finalMatches)}`;
        return { intent: "competition_summary", answer, data, note: "Penalty shoot-out details are not present in the supplied match columns." };
      }
      const rows = this.service.standings(year, competition ?? "Brasileirão Serie A");
      const selected = text.includes("relegat") ? rows.slice(-4) : rows;
      return {
        intent: "standings",
        answer: text.includes("won") || text.includes("winner") || text.includes("champion")
          ? (rows[0] ? `${rows[0].team} finished first in the calculated ${year} standings with ${rows[0].points} points.\n${formatStandings(rows.slice(0, 10))}` : formatStandings(rows))
          : formatStandings(selected),
        data: selected,
        note: "Standings are calculated only from complete match records in the provided dataset; knockout competitions are not league tables."
      };
    }

    if (/biggest (win|wins|victor)/.test(text) || /average goals|goals per match|home win rate/.test(text)) {
      const data = this.service.statistics({ competition, season: year, team: teams[0], limit: 10 });
      const answer = `${data.matches} matches, ${data.averageGoals} average goals per match; home win rate ${data.homeWinRate}%, away win rate ${data.awayWinRate}%, draws ${data.drawRate}%.\nBiggest victories:\n${formatMatches(data.biggestVictories)}`;
      return { intent: "statistics", answer, data };
    }

    if (teams[0] && /\b(record|statistics|stats|performance)\b/.test(text)) {
      const venue = text.includes("home") ? "home" : text.includes("away") ? "away" : "all";
      const data = this.service.teamStats(teams[0], { season: year, competition, venue });
      return { intent: "team_statistics", answer: formatTeamStats(data), data };
    }

    if (teams[0] && /what competitions|which competitions/.test(text)) {
      const result = this.service.searchMatches({ team: teams[0], season: year, limit: 200 });
      const competitions = [...new Set(result.items.map((match) => match.competition))].sort();
      return { intent: "team_competitions", answer: `${teams[0]} appears in: ${competitions.join(", ") || "no competitions found"}.`, data: competitions };
    }

    if (/best (home|away) record|most goals/.test(text)) {
      const matches = this.service.searchMatches({ competition, season: year, limit: 200 }).items;
      const teamNames = [...new Set(matches.flatMap((match) => [match.homeTeam, match.awayTeam]))];
      const venue = text.includes("home") ? "home" : text.includes("away") ? "away" : "all";
      const rows = teamNames.map((team) => this.service.teamStats(team, { competition, season: year, venue }))
        .filter((row) => row.matches > 0)
        .sort((a, b) => text.includes("most goals") ? b.goalsFor - a.goalsFor : b.winRate - a.winRate || b.matches - a.matches);
      return { intent: "team_ranking", answer: rows.slice(0, 10).map((row, index) => `${index + 1}. ${formatTeamStats(row)}`).join("\n"), data: rows.slice(0, 10) };
    }

    if (teams[0] || competition || year) {
      const result = this.service.searchMatches({ team: teams[0], competition, season: year, finals: /\bfinals?\b/.test(text), newestFirst: true, limit: 25 });
      return { intent: "match_search", answer: formatMatches(result.items, result.total), data: result };
    }

    return {
      intent: "help",
      answer: "I can search matches, compare teams, calculate team records and standings, find players, summarize competitions, and analyze goals or biggest victories. Include a team, competition, or season for the most precise result.",
      data: this.service.store.summary
    };
  }
}
