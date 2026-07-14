const BR_STATE_CODES = new Set([
  "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
  "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
  "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
]);

const KNOWN_ALIASES: Record<string, string> = {
  "sport club corinthians paulista": "Corinthians",
  "sao paulo futebol clube": "Sao Paulo",
};

export function stripAccents(value: string): string {
  return value.normalize("NFD").replace(/[̀-ͯ]/g, "");
}

export function splitStateSuffix(raw: string): { name: string; state?: string } {
  const name = raw.trim();

  const dashMatch = name.match(/^(.*)-([A-Za-z]{2})$/);
  if (dashMatch && BR_STATE_CODES.has(dashMatch[2].toUpperCase())) {
    return { name: dashMatch[1].trim(), state: dashMatch[2].toUpperCase() };
  }

  const spacedDashMatch = name.match(/^(.*)\s-\s([A-Za-z]{2})$/);
  if (spacedDashMatch && BR_STATE_CODES.has(spacedDashMatch[2].toUpperCase())) {
    return { name: spacedDashMatch[1].trim(), state: spacedDashMatch[2].toUpperCase() };
  }

  return { name };
}

export function normalizeTeamName(raw: string): string {
  const trimmed = raw.trim();

  const alias = KNOWN_ALIASES[stripAccents(trimmed).toLowerCase()];
  if (alias) return alias;

  return splitStateSuffix(trimmed).name;
}

export function teamKey(raw: string): string {
  const normalized = normalizeTeamName(raw);
  return stripAccents(normalized)
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");
}

export function teamsMatch(a: string, b: string): boolean {
  return teamKey(a) === teamKey(b);
}

function isAllUpperCase(value: string): boolean {
  return value === value.toUpperCase() && value !== value.toLowerCase();
}

function hasAccents(value: string): boolean {
  return value !== stripAccents(value);
}

function displayNameScore(value: string): number {
  let score = 0;
  if (hasAccents(value)) score += 10;
  if (!isAllUpperCase(value)) score += 5;
  return score;
}

function pickCanonicalName(names: string[]): string {
  const counts = new Map<string, number>();
  for (const name of names) counts.set(name, (counts.get(name) ?? 0) + 1);

  return [...counts.entries()].sort((a, b) => {
    const scoreDiff = displayNameScore(b[0]) - displayNameScore(a[0]);
    if (scoreDiff !== 0) return scoreDiff;
    const countDiff = b[1] - a[1];
    if (countDiff !== 0) return countDiff;
    return a[0].localeCompare(b[0]);
  })[0][0];
}

interface TeamOccurrence {
  homeTeam: string;
  awayTeam: string;
  homeTeamState?: string;
  awayTeamState?: string;
}

// A state variant is only treated as a genuinely distinct club (and given a
// "-UF" suffix) when it has a non-trivial share of that name's occurrences.
// Otherwise a single stray match from an obscure homonym club (e.g. a lower-
// division "Flamengo-PI" appearing once in an early Copa do Brasil round)
// would saddle a famous club like Flamengo with an unwanted "-RJ" suffix.
const MIN_VARIANT_COUNT = 3;
const MIN_VARIANT_SHARE = 0.05;

export function canonicalizeTeamNames<T extends TeamOccurrence>(matches: T[]): T[] {
  const variantsByKey = new Map<string, string[]>();
  const statesByKey = new Map<string, Map<string, number>>();

  const record = (name: string, state: string | undefined) => {
    const key = teamKey(name);
    const list = variantsByKey.get(key);
    if (list) list.push(name);
    else variantsByKey.set(key, [name]);

    if (state) {
      const states = statesByKey.get(key) ?? new Map<string, number>();
      states.set(state, (states.get(state) ?? 0) + 1);
      statesByKey.set(key, states);
    }
  };

  for (const m of matches) {
    record(m.homeTeam, m.homeTeamState);
    record(m.awayTeam, m.awayTeamState);
  }

  const canonicalByKey = new Map<string, string>();
  const canonicalByKeyAndState = new Map<string, string>();

  for (const [key, names] of variantsByKey) {
    const baseCanonical = pickCanonicalName(names);
    canonicalByKey.set(key, baseCanonical);

    const states = statesByKey.get(key);
    if (!states) continue;

    const total = [...states.values()].reduce((sum, n) => sum + n, 0);
    const qualifyingStates = [...states.entries()].filter(
      ([, count]) => count >= MIN_VARIANT_COUNT && count / total >= MIN_VARIANT_SHARE,
    );

    if (qualifyingStates.length > 1) {
      for (const [state] of qualifyingStates) {
        canonicalByKeyAndState.set(`${key}|${state}`, `${baseCanonical}-${state}`);
      }
    }
  }

  const resolve = (name: string, state: string | undefined): string => {
    const key = teamKey(name);
    if (state) {
      const disambiguated = canonicalByKeyAndState.get(`${key}|${state}`);
      if (disambiguated) return disambiguated;
    }
    return canonicalByKey.get(key)!;
  };

  return matches.map((m) => ({
    ...m,
    homeTeam: resolve(m.homeTeam, m.homeTeamState),
    awayTeam: resolve(m.awayTeam, m.awayTeamState),
  }));
}
