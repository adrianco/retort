/**
 * Traditional Brazilian rivalries (clássicos), keyed by team keys.
 */

const RIVALRIES: [string, string, string][] = [
  ['flamengo|RJ', 'fluminense|RJ', 'Fla-Flu'],
  ['flamengo|RJ', 'vasco|RJ', 'Clássico dos Milhões'],
  ['botafogo|RJ', 'flamengo|RJ', 'Clássico da Rivalidade'],
  ['fluminense|RJ', 'vasco|RJ', 'Clássico dos Gigantes'],
  ['botafogo|RJ', 'fluminense|RJ', 'Clássico Vovô'],
  ['botafogo|RJ', 'vasco|RJ', 'Clássico da Amizade'],
  ['corinthians|SP', 'palmeiras|SP', 'Derby Paulista'],
  ['palmeiras|SP', 'sao paulo|SP', 'Choque-Rei'],
  ['corinthians|SP', 'sao paulo|SP', 'Majestoso'],
  ['santos|SP', 'sao paulo|SP', 'San-São'],
  ['corinthians|SP', 'santos|SP', 'Clássico Alvinegro'],
  ['palmeiras|SP', 'santos|SP', 'Clássico da Saudade'],
  ['gremio|RS', 'internacional|RS', 'Grenal'],
  ['atletico|MG', 'cruzeiro|MG', 'Clássico Mineiro'],
  ['america|MG', 'atletico|MG', 'Clássico das Multidões Mineiro'],
  ['bahia|BA', 'vitoria|BA', 'Ba-Vi'],
  ['athletico|PR', 'coritiba|PR', 'Atletiba'],
  ['ceara|CE', 'fortaleza|CE', 'Clássico-Rei'],
  ['nautico|PE', 'sport|PE', 'Clássico dos Clássicos'],
  ['santa cruz|PE', 'sport|PE', 'Clássico das Multidões'],
  ['paysandu|PA', 'remo|PA', 'Re-Pa'],
  ['avai|SC', 'figueirense|SC', 'Clássico da Capital'],
  ['atletico|GO', 'goias|GO', 'Clássico Goiano'],
  ['boca juniors|', 'river plate|', 'Superclásico'],
];

const BY_PAIR = new Map<string, string>(RIVALRIES.map(([a, b, name]) => [[a, b].sort().join(' v '), name]));

export function derbyName(home: string, away: string): string | undefined {
  return BY_PAIR.get([home, away].sort().join(' v '));
}
