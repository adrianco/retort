const ALIASES: Record<string, string> = {
  "sao paulo fc": "sao paulo", "sao paulo futebol clube": "sao paulo",
  "sport club corinthians paulista": "corinthians", "corinthians paulista": "corinthians",
  "clube de regatas do flamengo": "flamengo", "flamengo rj": "flamengo",
  "sociedade esportiva palmeiras": "palmeiras", "santos fc": "santos",
  // Do not collapse the two Atlético clubs merely because their feeds use a
  // state suffix. They are distinct teams in standings and statistics.
  "atletico mg": "atletico mineiro", "atletico pr": "athletico paranaense",
  "athletico pr": "athletico paranaense",
};

export function normalise(value: string): string {
  const raw = value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase()
    .replace(/[^a-z0-9 ]/g, " ").replace(/\s+/g, " ").trim();
  const withoutState = raw.replace(/\s+[a-z]{2}$/i, "");
  return ALIASES[raw] ?? ALIASES[withoutState] ?? withoutState;
}

export function sameTeam(left: string, right: string): boolean {
  const a = normalise(left), b = normalise(right);
  return a === b || a.includes(b) || b.includes(a);
}

/** A stable key for grouping data which uses state suffixes inconsistently. */
export function teamKey(value: string): string {
  return normalise(value);
}

/** Keep the dataset spelling, but remove the state suffix used in some feeds. */
export function displayTeamName(value: string): string {
  return value.trim().replace(/\s*-\s*[A-Z]{2}$/i, "");
}
