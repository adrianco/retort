// State abbreviations used in Brazilian soccer datasets
const STATE_CODES = new Set([
  'AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
  'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN',
  'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO',
]);

export function normalizeTeamName(name: string): string {
  const trimmed = name.trim();
  // Handle "Team - XX" format (space before dash)
  const spaceMatch = trimmed.match(/^(.+?)\s+-\s+([A-Z]{2})$/);
  if (spaceMatch && STATE_CODES.has(spaceMatch[2])) {
    return spaceMatch[1].trim();
  }
  // Handle "Team-XX" format (no space)
  const dashMatch = trimmed.match(/^(.+)-([A-Z]{2})$/);
  if (dashMatch && STATE_CODES.has(dashMatch[2])) {
    return dashMatch[1].trim();
  }
  return trimmed;
}

function removeDiacritics(str: string): string {
  return str.normalize('NFD').replace(/[̀-ͯ]/g, '');
}

export function teamsMatch(query: string, teamName: string): boolean {
  const normalizedQuery = normalizeTeamName(query).toLowerCase();
  const normalizedTeam = normalizeTeamName(teamName).toLowerCase();

  if (normalizedQuery === normalizedTeam) return true;

  // Partial match: query is contained in team name
  if (normalizedTeam.includes(normalizedQuery) && normalizedQuery.length >= 4) {
    return true;
  }

  // Diacritics-insensitive comparison
  const queryNoDia = removeDiacritics(normalizedQuery);
  const teamNoDia = removeDiacritics(normalizedTeam);
  if (queryNoDia === teamNoDia) return true;
  if (teamNoDia.includes(queryNoDia) && queryNoDia.length >= 4) return true;

  return false;
}

export function parseDate(dateStr: string): Date | null {
  if (!dateStr || dateStr.trim() === '') return null;

  // Brazilian format: DD/MM/YYYY
  const brMatch = dateStr.match(/^(\d{2})\/(\d{2})\/(\d{4})/);
  if (brMatch) {
    const [, day, month, year] = brMatch;
    return new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
  }

  // ISO format with optional time: YYYY-MM-DD[ HH:MM:SS]
  const isoMatch = dateStr.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (isoMatch) {
    const [, year, month, day] = isoMatch;
    return new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
  }

  return null;
}

export function formatDate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

export function extractYear(dateStr: string): number | null {
  const d = parseDate(dateStr);
  return d ? d.getFullYear() : null;
}
