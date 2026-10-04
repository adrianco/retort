/** Brazil's traditional rivalries, keyed by the two clubs' team keys. */
import { fold } from './text.js';

const RIVALRIES: Array<[string, string, string]> = [
  ['Flamengo', 'Fluminense', 'Fla-Flu'],
  ['Flamengo', 'Vasco da Gama', 'Clássico dos Milhões'],
  ['Flamengo', 'Botafogo', 'Clássico da Rivalidade'],
  ['Fluminense', 'Vasco da Gama', 'Clássico dos Gigantes'],
  ['Botafogo', 'Fluminense', 'Clássico Vovô'],
  ['Botafogo', 'Vasco da Gama', 'Clássico da Amizade'],
  ['Corinthians', 'Palmeiras', 'Derby Paulista'],
  ['Corinthians', 'São Paulo', 'Majestoso'],
  ['Palmeiras', 'São Paulo', 'Choque-Rei'],
  ['Santos', 'São Paulo', 'San-São'],
  ['Corinthians', 'Santos', 'Clássico Alvinegro'],
  ['Palmeiras', 'Santos', 'Clássico da Saudade'],
  ['Grêmio', 'Internacional', 'Grenal'],
  ['Atlético Mineiro', 'Cruzeiro', 'Clássico Mineiro'],
  ['Bahia', 'Vitória', 'Ba-Vi'],
  ['Athletico Paranaense', 'Coritiba', 'Atletiba'],
  ['Sport', 'Santa Cruz', 'Clássico das Multidões'],
  ['Sport', 'Náutico', 'Clássico dos Clássicos'],
  ['Náutico', 'Santa Cruz', 'Clássico das Emoções'],
  ['Ceará', 'Fortaleza', 'Clássico-Rei'],
  ['Avaí', 'Figueirense', 'Clássico da Capital'],
  ['Paysandu', 'Remo', 'Re-Pa'],
  ['Goiás', 'Vila Nova', 'Clássico Goiano'],
];

const BY_PAIR = new Map<string, string>();
for (const [a, b, name] of RIVALRIES) {
  BY_PAIR.set(`${fold(a)}|${fold(b)}`, name);
  BY_PAIR.set(`${fold(b)}|${fold(a)}`, name);
}

export function derbyBetween(homeKey: string, awayKey: string): string | undefined {
  return BY_PAIR.get(`${homeKey}|${awayKey}`);
}

export function allDerbies(): string[] {
  return RIVALRIES.map(([a, b, name]) => `${name}: ${a} vs ${b}`);
}
