const STATE_CODES = new Set([
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
  'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
  'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
]);

export function stripAccents(value: string): string {
  return value.normalize('NFD').replace(/[̀-ͯ]/g, '');
}

export function normalizeTeamName(raw: string | undefined | null): string {
  if (!raw) return '';
  let name = String(raw).trim();

  // Drop trailing parenthesized country code: "Nacional (URU)"
  name = name.replace(/\s*\([A-Z]{2,3}\)$/, '').trim();

  // Drop trailing 3-letter country code with dash: "Barcelona-EQU"
  name = name.replace(/\s*-\s*[A-Z]{3}$/, '').trim();

  // Drop trailing state suffix with dash: "Palmeiras-SP", "Flamengo - RJ"
  const dashStateMatch = name.match(/^(.*?)\s*-\s*([A-Z]{2})$/);
  if (dashStateMatch && STATE_CODES.has(dashStateMatch[2])) {
    name = dashStateMatch[1].trim();
  }

  // Drop trailing state suffix space-separated: "Boavista SP"
  const trailingMatch = name.match(/^(.*?)\s+([A-Z]{2})$/);
  if (trailingMatch && STATE_CODES.has(trailingMatch[2])) {
    name = trailingMatch[1].trim();
  }

  return name.trim();
}

export function teamKey(raw: string | undefined | null): string {
  const normalized = normalizeTeamName(raw);
  return stripAccents(normalized).toLowerCase().replace(/[^a-z0-9]+/g, '');
}

export function teamMatches(target: string, candidate: string): boolean {
  if (!target || !candidate) return false;
  const t = teamKey(target);
  const c = teamKey(candidate);
  if (!t || !c) return false;
  return c === t || c.includes(t) || t.includes(c);
}

export function teamMatchesExact(target: string, candidate: string): boolean {
  return teamKey(target) === teamKey(candidate);
}
