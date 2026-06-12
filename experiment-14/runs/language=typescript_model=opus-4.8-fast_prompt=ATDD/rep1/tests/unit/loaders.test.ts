/**
 * Unit test: every provided CSV file is loaded and contributes rows, and the
 * documented competitions are represented.
 */
import { describe, it, expect } from 'vitest';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { DataStore } from '../../src/data/store.js';
import { loadInto } from '../../src/data/loaders.js';

const dataDir = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '../../data/kaggle',
);

describe('loadInto', () => {
  it('loads rows from all six provided CSV files', () => {
    const store = new DataStore();
    const report = loadInto(store, dataDir);

    for (const file of [
      'Brasileirao_Matches.csv',
      'Brazilian_Cup_Matches.csv',
      'Libertadores_Matches.csv',
      'BR-Football-Dataset.csv',
      'novo_campeonato_brasileiro.csv',
      'fifa_data.csv',
    ]) {
      expect(report.files[file]).toBeGreaterThan(0);
    }

    expect(report.totalMatches).toBeGreaterThan(20000);
    expect(report.totalPlayers).toBeGreaterThan(15000);
    expect(store.competitions()).toEqual(
      expect.arrayContaining(['Brasileirão', 'Copa do Brasil', 'Libertadores']),
    );
  });
});
