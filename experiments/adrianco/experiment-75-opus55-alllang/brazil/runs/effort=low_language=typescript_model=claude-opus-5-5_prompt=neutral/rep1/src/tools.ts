import type { Dataset } from "./data.js";
import * as Q from "./queries.js";

export type ToolArgs = Record<string, any>;

/** Tool handlers return plain text; kept separate from the MCP transport so they are unit-testable. */
export function createHandlers(ds: Dataset): Record<string, (a: ToolArgs) => string> {
  const more = (n: number, shown: number) => (n > shown ? [`- ... (${n - shown} more matches in dataset)`] : []);
  return {
    search_matches(a) {
      const ms = Q.findMatches(ds, a);
      if (!ms.length) return "No matches found for the given criteria.";
      const lim = a.limit ?? 20;
      return [`Found ${ms.length} matches:`, ...ms.slice(0, lim).map((m) => "- " + Q.formatMatch(m)), ...more(ms.length, lim)].join("\n");
    },
    head_to_head(a) {
      const h = Q.headToHead(ds, a.teamA, a.teamB, a.competition);
      if (!h.matches.length) return `No matches found between ${a.teamA} and ${a.teamB}.`;
      const derby = Q.RIVALRIES.find((r) => r.teams.includes(h.matches[0].homeKey) && r.teams.includes(h.matches[0].awayKey));
      const lim = a.limit ?? 10;
      return [
        `${h.teamA} vs ${h.teamB}${derby ? ` (${derby.name} derby)` : ""}:`,
        ...h.matches.slice(0, lim).map((m) => "- " + Q.formatMatch(m)), ...more(h.matches.length, lim), "",
        `Head-to-head in dataset (${h.matches.length} matches): ${h.teamA} ${h.winsA} wins, ${h.teamB} ${h.winsB} wins, ${h.draws} draws`,
        `Goals: ${h.teamA} ${h.goalsA} - ${h.goalsB} ${h.teamB}`,
      ].join("\n");
    },
    team_stats(a) {
      const { record, byCompetition, ambiguous } = Q.teamRecord(ds, a.team, a);
      if (!record.matches) return `No matches found for ${a.team} with those filters.`;
      const venue = a.venue && a.venue !== "any" ? `${a.venue} ` : "";
      const scope = [a.season, a.competition ? Q.parseCompetition(a.competition) : undefined].filter(Boolean).join(" ");
      const out = [Q.formatRecord(record, `${record.team} ${venue}record${scope ? ` (${scope})` : ""}`)];
      if (ambiguous) out.push(`Note: "${a.team}" matches several clubs (${ambiguous.join(", ")}); add a state, e.g. "${ambiguous[0]}".`);
      if (byCompetition.length > 1) {
        out.push("", "By competition:", ...byCompetition.map((r) => `- ${r.team}: ${r.matches} matches, ${r.wins}W ${r.draws}D ${r.losses}L, GF ${r.goalsFor} GA ${r.goalsAgainst}`));
      }
      return out.join("\n");
    },
    standings(a) {
      const comp = Q.parseCompetition(a.competition ?? "Brasileirão")!;
      const rows = Q.standings(ds, a.season, comp);
      return Q.formatStandings(a.top ? rows.slice(0, a.top) : rows, a.season, comp);
    },
    competition_stats(a) {
      const s = Q.competitionStats(ds, a);
      return [
        `${s.competition}${s.season ? ` ${s.season}` : ""} statistics (provided data):`,
        `- Matches: ${s.matches}, Goals: ${s.goals}`,
        `- Average goals per match: ${s.avgGoals.toFixed(2)}`,
        `- Home win rate: ${(s.homeWinRate * 100).toFixed(1)}%, Away win rate: ${(s.awayWinRate * 100).toFixed(1)}%, Draw rate: ${(s.drawRate * 100).toFixed(1)}%`,
        `- Top scoring teams: ${s.topScoringTeams.map((t) => `${t.team} (${t.goals})`).join(", ")}`,
      ].join("\n");
    },
    biggest_wins(a) {
      const ms = Q.biggestWins(ds, a);
      return ["Biggest victories (provided data):", ...ms.map((m, i) => `${i + 1}. ${Q.formatMatch(m)}`)].join("\n");
    },
    best_records(a) {
      const rows = Q.bestRecords(ds, a as any);
      return [`Best ${a.venue} records (points per game, min ${a.minMatches ?? 10} matches):`,
        ...rows.map((r, i) => `${i + 1}. ${r.team} - ${r.matches} matches, ${r.wins}W ${r.draws}D ${r.losses}L, ${(r.points / r.matches).toFixed(2)} pts/game, win rate ${((100 * r.wins) / r.matches).toFixed(1)}%`)].join("\n");
    },
    team_competitions(a) {
      const cs = Q.teamCompetitions(ds, a.team);
      if (!cs.length) return `No matches found for ${a.team}.`;
      return [`Competitions played by ${a.team} in the dataset:`, ...cs.map((c) => `- ${c.competition}: seasons ${c.seasons.join(", ")}`)].join("\n");
    },
    derbies(a) {
      const ds_ = Q.derbies(ds, a);
      if (!ds_.length) return "No derby matches found.";
      const lim = a.limit ?? 30;
      return [`Derby matches (${ds_.length}):`, ...ds_.slice(0, lim).map((d) => `- [${d.derby}] ${Q.formatMatch(d.match)}`), ...more(ds_.length, lim)].join("\n");
    },
    search_players(a) {
      const ps = Q.searchPlayers(ds, { ...a, limit: a.limit ?? 25 });
      if (!ps.length) return "No players found matching those criteria (note: the FIFA dataset does not include every Brazilian club, e.g. Flamengo, Palmeiras, Corinthians and São Paulo are absent).";
      const total = Q.searchPlayers(ds, { ...a, limit: Infinity }).length;
      return [`Players found: ${total}${total > ps.length ? ` (showing top ${ps.length})` : ""}`, ...ps.map((p, i) => Q.formatPlayer(p, i))].join("\n");
    },
    get_player(a) {
      const ps = Q.searchPlayers(ds, { name: a.name, limit: 5 });
      if (!ps.length) return `No player named "${a.name}" found in the FIFA dataset.`;
      return [Q.playerDetail(ps[0]), ...(ps.length > 1 ? ["", "Other matches:", ...ps.slice(1).map((p) => Q.formatPlayer(p))] : [])].join("\n");
    },
    brazilian_club_players(a) {
      const rows = Q.brazilianClubPlayers(ds, a);
      return [`${a.brazilianOnly ? "Brazilian players" : "Players"} at Brazilian clubs (FIFA data):`,
        ...rows.map((r) => `- ${r.club}: ${r.count} players (avg rating: ${r.avgOverall}; best: ${r.best.name} ${r.best.overall})`)].join("\n");
    },
    team_profile(a) {
      const { record } = Q.teamRecord(ds, a.team);
      const comps = Q.teamCompetitions(ds, a.team);
      const players = Q.searchPlayers(ds, { club: a.team, limit: 5 });
      return [
        Q.formatRecord(record, `${record.team} all-time record in dataset`), "",
        "Competitions:", ...comps.map((c) => `- ${c.competition}: ${c.seasons.length} seasons (${c.seasons[0]}-${c.seasons[c.seasons.length - 1]})`), "",
        "Top FIFA-rated players at the club:", ...(players.length ? players.map((p, i) => Q.formatPlayer(p, i)) : ["- none in FIFA dataset"]),
      ].join("\n");
    },
    dataset_info() {
      return ["Loaded datasets (valid rows):", ...Object.entries(ds.fileCounts).map(([f, n]) => `- ${f}: ${n}`),
        `Série A seasons with standings: ${[...ds.serieA.keys()].sort().join(", ")}`].join("\n");
    },
  };
}
