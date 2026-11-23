import { club, day, files, fold, Graph, league, type Match } from "./data.js";

type Property = {
  type: "string" | "integer" | "boolean";
  description?: string;
  enum?: string[];
  minimum?: number;
  maximum?: number;
};
const string = (description: string): Property => ({
  type: "string",
  description,
});
const choice = (...values: string[]): Property => ({
  type: "string",
  enum: values,
});
const page = {
  limit: { type: "integer", minimum: 1, maximum: 100 },
  offset: { type: "integer", minimum: 0 },
} as const;
const filters = {
  team: string("Club in either role unless venue is specified"),
  opponent: string("Opponent of team"),
  venue: choice("home", "away", "either"),
  competition: string(
    "Serie A (Brasileirão), Serie B, Serie C, Copa do Brasil or Copa Libertadores",
  ),
  season: { type: "integer" } as Property,
  from: string("Inclusive date YYYY-MM-DD or DD/MM/YYYY"),
  to: string("Inclusive end date"),
  stage: string(
    "Exact stage, e.g. final, semifinals, quarterfinals, round of 16, group stage",
  ),
  round: string("Round number"),
  derby: { type: "boolean" } as Property,
  source: choice(...files),
};
function tool(
  name: string,
  description: string,
  properties: Record<string, Property>,
) {
  return {
    name,
    description,
    inputSchema: { type: "object", properties, additionalProperties: false },
  };
}
export const tools = [
  tool(
    "matches",
    "Search fixture history, scores, schedules, derby pairs and knockout brackets. Latest dated fixtures first. Use source for original row details.",
    {
      ...filters,
      ...page,
      order: choice("latest", "earliest", "biggest_win"),
      played: { type: "boolean" },
    },
  ),
  tool(
    "records",
    "Calculate team or head-to-head records. Rank teams by points (league standings), goals or win rate. Venue restricts the perspective of each record.",
    { ...filters, ...page, sort: choice("points", "goals", "win_rate") },
  ),
  tool(
    "statistics",
    "Totals, average goals and home/away performance over completed games. Group by season for trends or by competition for participation.",
    { ...filters, group: choice("all", "season", "competition") },
  ),
  tool(
    "players",
    "Search FIFA snapshot by name, club, nationality or position. Highest Overall first. Use details for all original player attributes.",
    {
      ...page,
      name: string("Partial player name"),
      club: string("Club name or substring"),
      nationality: string("Country e.g. Brazil"),
      position: string("Position code or forward"),
      details: { type: "boolean" },
    },
  ),
];
type Args = {
  team?: string;
  opponent?: string;
  venue?: string;
  competition?: string;
  season?: number;
  from?: string;
  to?: string;
  stage?: string;
  round?: string;
  derby?: boolean;
  source?: string;
  limit?: number;
  offset?: number;
  order?: string;
  played?: boolean;
  sort?: string;
  group?: string;
  name?: string;
  club?: string;
  nationality?: string;
  position?: string;
  details?: boolean;
};
function validate(name: string, input: unknown): Args {
  const t = tools.find((t) => t.name === name);
  if (!t) throw Error("Unknown tool " + name);
  if (!input || typeof input !== "object" || Array.isArray(input))
    throw Error("Expected arguments object");
  for (const [k, v] of Object.entries(input)) {
    const p = t.inputSchema.properties[k];
    if (
      !Object.hasOwn(t.inputSchema.properties, k) ||
      (p.type === "integer" ? !Number.isSafeInteger(v) : typeof v !== p.type) ||
      (p.enum && !p.enum.includes(v)) ||
      (p.minimum !== undefined && v < p.minimum) ||
      (p.maximum !== undefined && v > p.maximum)
    )
      throw Error("Invalid " + k);
  }
  const a = input as Args;
  for (const d of [a.from, a.to])
    if (d !== undefined) {
      const normalized = day(d),
        time = Date.parse(normalized);
      if (
        !/^(?:\d{4}-\d{2}-\d{2}|\d{2}\/\d{2}\/\d{4})$/.test(d) ||
        !Number.isFinite(time) ||
        new Date(time).toISOString().slice(0, 10) !== normalized
      )
        throw Error("Invalid date");
    }
  if (a.from && a.to && day(a.from) > day(a.to))
    throw Error("Reversed date range");
  if (a.opponent && !a.team) throw Error("Specify team with opponent");
  return a;
}
const derbies = new Set([
  "flamengo|fluminense",
  "flamengo|vasco da gama",
  "corinthians|palmeiras",
  "palmeiras|sao paulo",
  "corinthians|sao paulo",
  "gremio|internacional",
  "atletico mg|cruzeiro",
  "bahia|vitoria",
  "ceara|fortaleza",
  "atletico pr|coritiba",
  "nautico|sport",
  "botafogo|fluminense",
]);
const completed = (m: Match) => m.homeGoals !== null && m.awayGoals !== null;
function paginate<T>(rows: T[], a: Args) {
  const offset = a.offset ?? 0,
    limit = a.limit ?? 20;
  return {
    total: rows.length,
    offset,
    results: rows.slice(offset, offset + limit),
  };
}
export function query(graph: Graph, name: string, input: unknown = {}) {
  const a = validate(name, input);
  if (name === "players") {
    const position = fold(a.position ?? "");
    const positions = ["forward", "forwards"].includes(position)
      ? ["st", "ls", "rs", "cf", "lf", "rf", "lw", "rw"]
      : [position];
    const results = graph.players.filter(
      (p) =>
        (!a.name || fold(p.Name).includes(fold(a.name))) &&
        (!a.club || club(p.Club).includes(club(a.club))) &&
        (!a.nationality ||
          fold(p.Nationality) ===
            fold(a.nationality).replace(/^brazilian$/, "brazil")) &&
        (!position || positions.includes(fold(p.Position))),
    );
    const page = paginate(results, a);
    return {
      ...page,
      results: page.results.map((p) =>
        a.details
          ? p
          : {
              id: p.ID,
              name: p.Name,
              club: p.Club,
              nationality: p.Nationality,
              overall: +p.Overall,
              potential: +p.Potential,
              position: p.Position,
            },
      ),
    };
  }
  const team = club(a.team ?? ""),
    opponent = club(a.opponent ?? ""),
    comp = fold(league(a.competition ?? ""));
  const from = day(a.from ?? ""),
    to = day(a.to ?? "");
  const matches = (
    a.source ? graph.sourceMatches.get(a.source)! : graph.matches
  ).filter((m) => {
    if (
      team &&
      !(
        (team === m.home &&
          a.venue !== "away" &&
          (!opponent || opponent === m.away)) ||
        (team === m.away &&
          a.venue !== "home" &&
          (!opponent || opponent === m.home))
      )
    )
      return false;
    return (
      (!comp || fold(m.competition) === comp) &&
      (a.season === undefined || m.season === a.season) &&
      (!from || m.date >= from) &&
      (!to || (!!m.date && m.date <= to)) &&
      (!a.round || m.round === a.round) &&
      (!a.stage || fold(m.stage) === fold(a.stage)) &&
      (a.played === undefined || a.played === completed(m)) &&
      (!a.derby || derbies.has([m.home, m.away].sort().join("|")))
    );
  });
  if (name === "matches") {
    const margin = (m: Match) => Math.abs(m.homeGoals! - m.awayGoals!);
    const ordered =
      a.order === "biggest_win"
        ? matches.filter((m) => completed(m) && margin(m) > 0)
        : matches;
    ordered.sort(
      (x, y) =>
        (a.order === "biggest_win" ? margin(y) - margin(x) : 0) ||
        (a.order === "earliest"
          ? (x.date || "~").localeCompare(y.date || "~")
          : y.date.localeCompare(x.date)),
    );
    const page = paginate(ordered, a);
    return {
      ...page,
      results: page.results.map(({ details, ...m }) =>
        a.source ? { ...m, details } : m,
      ),
    };
  }
  if (name === "records") {
    const rows = new Map<
      string,
      {
        team: string;
        matches: number;
        wins: number;
        draws: number;
        losses: number;
        goalsFor: number;
        goalsAgainst: number;
      }
    >();
    for (const m of matches.filter(completed)) {
      for (const home of [true, false]) {
        const key = home ? m.home : m.away;
        if (
          (team && key !== team) ||
          (home ? a.venue === "away" : a.venue === "home")
        )
          continue;
        const r = rows.get(key) ?? {
          team: key,
          matches: 0,
          wins: 0,
          draws: 0,
          losses: 0,
          goalsFor: 0,
          goalsAgainst: 0,
        };
        const gf = home ? m.homeGoals! : m.awayGoals!,
          ga = home ? m.awayGoals! : m.homeGoals!;
        r.matches++;
        r[gf > ga ? "wins" : gf < ga ? "losses" : "draws"]++;
        r.goalsFor += gf;
        r.goalsAgainst += ga;
        rows.set(key, r);
      }
    }
    const results = [...rows.values()].map((r) => ({
      ...r,
      points: 3 * r.wins + r.draws,
      goalDifference: r.goalsFor - r.goalsAgainst,
      winRate: (100 * r.wins) / r.matches,
    }));
    return paginate(
      results.sort(
        (x, y) =>
          (a.sort === "goals"
            ? y.goalsFor - x.goalsFor
            : a.sort === "win_rate"
              ? y.winRate - x.winRate
              : 0) ||
          y.points - x.points ||
          y.wins - x.wins ||
          y.goalDifference - x.goalDifference ||
          y.goalsFor - x.goalsFor ||
          x.team.localeCompare(y.team),
      ),
      a,
    );
  }
  const groups = new Map<string, Match[]>();
  if (!a.group || a.group === "all") groups.set("all", []);
  for (const m of matches) {
    const key =
      a.group === "competition"
        ? m.competition
        : a.group === "season"
          ? String(m.season)
          : "all";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(m);
  }
  return [...groups.entries()]
    .sort(([x], [y]) => x.localeCompare(y))
    .map(([group, fixtures]) => {
      const played = fixtures.filter(completed);
      let goals = 0,
        homeWins = 0,
        awayWins = 0;
      for (const m of played) {
        goals += m.homeGoals! + m.awayGoals!;
        homeWins += Number(m.homeGoals! > m.awayGoals!);
        awayWins += Number(m.homeGoals! < m.awayGoals!);
      }
      return {
        group,
        fixtures: fixtures.length,
        played: played.length,
        goals,
        homeWins,
        awayWins,
        draws: played.length - homeWins - awayWins,
        averageGoals: played.length ? goals / played.length : null,
        homeWinRate: played.length ? (100 * homeWins) / played.length : null,
      };
    });
}
