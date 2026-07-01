const ALIASES: Record<string, string> = {
  'sport club corinthians paulista': 'Corinthians',
  'sao paulo futebol clube': 'São Paulo',
  'sao paulo fc': 'São Paulo',
};

const STATE_SUFFIXES = /-(AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)$/i;

function extractState(name: string): string | null {
  const m = name.trim().match(STATE_SUFFIXES);
  return m ? m[1].toUpperCase() : null;
}

export function normalizeTeamName(name: string): string {
  const trimmed = name.trim();
  const lower = trimmed.toLowerCase();

  if (ALIASES[lower]) return ALIASES[lower];

  return trimmed.replace(STATE_SUFFIXES, '').trim();
}

const accentFold = (s: string) =>
  s.normalize('NFD').replace(/[̀-ͯ]/g, '');

export function teamsMatch(a: string, b: string): boolean {
  const stateA = extractState(a);
  const stateB = extractState(b);

  // If both sides specify a state and they differ, they're different teams
  if (stateA && stateB && stateA !== stateB) return false;

  const normA = accentFold(normalizeTeamName(a).toLowerCase());
  const normB = accentFold(normalizeTeamName(b).toLowerCase());

  return normA === normB;
}
