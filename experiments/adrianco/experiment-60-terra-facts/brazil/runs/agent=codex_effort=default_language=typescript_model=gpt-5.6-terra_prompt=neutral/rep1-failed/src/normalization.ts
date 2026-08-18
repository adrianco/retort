const ALIASES: Record<string, string> = {
  "sao paulo fc": "sao paulo", "sao paulo futebol clube": "sao paulo",
  "sport club corinthians paulista": "corinthians", "corinthians paulista": "corinthians",
  "clube de regatas do flamengo": "flamengo", "flamengo rj": "flamengo",
  "sociedade esportiva palmeiras": "palmeiras", "santos fc": "santos",
};

export function normalise(value: string): string {
  const basic = value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase()
    .replace(/\s*-\s*[a-z]{2}$/i, "").replace(/[^a-z0-9 ]/g, " ").replace(/\s+/g, " ").trim();
  return ALIASES[basic] ?? basic;
}

export function sameTeam(left: string, right: string): boolean {
  const a = normalise(left), b = normalise(right);
  return a === b || a.includes(b) || b.includes(a);
}
