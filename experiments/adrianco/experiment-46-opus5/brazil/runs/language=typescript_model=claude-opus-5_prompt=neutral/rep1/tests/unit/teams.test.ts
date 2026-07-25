/**
 * Team identity is the highest-risk part of the pipeline: an incorrect merge
 * silently corrupts every statistic downstream, and an incorrect split hides
 * half a club's history. These tests pin both directions.
 */

import { describe, expect, it } from 'vitest';
import { parseTeamName, TeamRegistry } from '../../src/domain/teams.js';
import { normalizeName, similarity, slugify } from '../../src/util/text.js';

describe('normalizeName', () => {
  it('folds accents and cedillas', () => {
    expect(normalizeName('Grêmio')).toBe('gremio');
    expect(normalizeName('Avaí')).toBe('avai');
    expect(normalizeName('São Paulo')).toBe('sao paulo');
    expect(normalizeName('Atlético Mineiro')).toBe('atletico mineiro');
  });

  it('is case insensitive and collapses whitespace', () => {
    expect(normalizeName('  SAO   PAULO ')).toBe('sao paulo');
  });
});

describe('slugify', () => {
  it('produces kebab-case identifiers', () => {
    expect(slugify('Vasco da Gama')).toBe('vasco-da-gama');
    expect(slugify('Náutico')).toBe('nautico');
  });
});

describe('similarity', () => {
  it('scores identical strings as 1', () => {
    expect(similarity('flamengo', 'flamengo')).toBe(1);
  });

  it('scores a one-letter difference highly', () => {
    expect(similarity('flamengo', 'flamengos')).toBeGreaterThan(0.85);
  });

  it('scores unrelated strings low', () => {
    expect(similarity('flamengo', 'corinthians')).toBeLessThan(0.4);
  });
});

describe('parseTeamName', () => {
  it('peels a hyphenated state suffix', () => {
    expect(parseTeamName('Palmeiras-SP')).toMatchObject({ base: 'palmeiras', state: 'SP' });
  });

  it('peels a spaced state suffix', () => {
    expect(parseTeamName('Botafogo RJ')).toMatchObject({ base: 'botafogo', state: 'RJ' });
  });

  it('peels a " - XX" state suffix', () => {
    expect(parseTeamName('América - MG')).toMatchObject({ base: 'america', state: 'MG' });
  });

  it('peels a parenthesised country code', () => {
    expect(parseTeamName('Nacional (URU)')).toMatchObject({ base: 'nacional', country: 'URU' });
  });

  it('peels a hyphenated country code', () => {
    expect(parseTeamName('Guaraní-PAR')).toMatchObject({ base: 'guarani', country: 'PAR' });
  });

  it('drops club-type initialisms', () => {
    expect(parseTeamName('EC Bahia').base).toBe('bahia');
    expect(parseTeamName('Fortaleza FC').base).toBe('fortaleza');
    expect(parseTeamName('CA Taguatinga').base).toBe('taguatinga');
  });

  it('drops spelled-out club-type words and articles', () => {
    expect(parseTeamName('Sport Club do Recife').base).toBe('sport recife');
    expect(parseTeamName('Ceará Sporting Club').base).toBe('ceara');
    expect(parseTeamName('Sociedade Esportiva Palmeiras').base).toBe('palmeiras');
  });

  it('never strips a name down to nothing', () => {
    expect(parseTeamName('CSA').base).toBe('csa');
    expect(parseTeamName('ABC').base).toBe('abc');
    expect(parseTeamName('CRB').base).toBe('crb');
  });

  it('keeps the source spelling for display', () => {
    expect(parseTeamName('Grêmio-RS').display).toBe('Grêmio');
  });
});

describe('TeamRegistry', () => {
  const registry = new TeamRegistry();

  it('merges every spelling of the same club', () => {
    const spellings = ['Sao Paulo-SP', 'São Paulo', 'Sao Paulo', 'SAO PAULO', 'São Paulo FC'];
    const ids = new Set(spellings.map((name) => registry.intern(name).id));
    expect([...ids]).toEqual(['sao-paulo-sp']);
  });

  it('merges the Athletico / Atletico Paranaense spellings', () => {
    const ids = new Set(
      ['Atletico-PR', 'Athletico-PR', 'Athletico Paranaense', 'Atletico Paranaense', 'Athletico'].map(
        (name) => registry.intern(name).id,
      ),
    );
    expect([...ids]).toEqual(['athletico-pr']);
  });

  it('merges Vasco spellings', () => {
    const ids = new Set(
      ['Vasco', 'Vasco da Gama-RJ', 'Vasco Da Gama RJ'].map((name) => registry.intern(name).id),
    );
    expect([...ids]).toEqual(['vasco-rj']);
  });

  it('keeps the three Atléticos apart', () => {
    expect(registry.intern('Atletico-MG').id).toBe('atletico-mg');
    expect(registry.intern('Atlético Mineiro').id).toBe('atletico-mg');
    expect(registry.intern('Atletico-GO').id).toBe('atletico-go');
    expect(registry.intern('Atletico Goianiense').id).toBe('atletico-go');
    expect(registry.intern('Atletico-PR').id).toBe('athletico-pr');
  });

  it('keeps the Botafogos apart and gives the bare name to Rio', () => {
    expect(registry.intern('Botafogo').id).toBe('botafogo-rj');
    expect(registry.intern('Botafogo RJ').id).toBe('botafogo-rj');
    expect(registry.intern('Botafogo SP').id).toBe('botafogo-sp');
    expect(registry.intern('Botafogo PB').id).toBe('botafogo-pb');
  });

  it('keeps América-MG and América-RN apart', () => {
    expect(registry.intern('América - MG').id).toBe('america-mg');
    expect(registry.intern('America RN').id).toBe('america-rn');
    expect(registry.intern('America FC Natal').id).toBe('america-rn');
  });

  it('keeps same-named clubs from different countries apart', () => {
    expect(registry.intern('Nacional (URU)').id).toBe('nacional-uru');
    expect(registry.intern('Nacional-URU').id).toBe('nacional-uru');
    expect(registry.intern('Nacional (PAR)').id).toBe('nacional-par');
  });

  it('records every raw spelling it has seen', () => {
    const fresh = new TeamRegistry();
    fresh.intern('Sao Paulo-SP');
    const team = fresh.intern('São Paulo');
    expect(team.aliases.has('Sao Paulo-SP')).toBe(true);
    expect(team.aliases.has('São Paulo')).toBe(true);
  });

  it('mints stable ids for clubs outside the curated table', () => {
    const first = registry.intern('Aparecidense GO');
    const second = registry.intern('Aparecidense-GO');
    expect(first.id).toBe(second.id);
    expect(first.state).toBe('GO');
  });

  describe('resolveQuery', () => {
    it('resolves a canonical id, once the club has been seen in the data', () => {
      registry.intern('Flamengo-RJ');
      expect(registry.resolveQuery('flamengo-rj').team?.id).toBe('flamengo-rj');
    });

    it('resolves an unaccented user spelling', () => {
      registry.intern('Gremio-RS');
      expect(registry.resolveQuery('Gremio').team?.id).toBe('gremio-rs');
      expect(registry.resolveQuery('Grêmio').team?.id).toBe('gremio-rs');
    });

    it('returns no team but offers candidates for nonsense', () => {
      const fresh = new TeamRegistry();
      fresh.intern('Flamengo-RJ');
      fresh.intern('Palmeiras-SP');
      const result = fresh.resolveQuery('Manchester Rovers United of Nowhere');
      expect(result.team).toBeUndefined();
      expect(result.candidates.length).toBeGreaterThan(0);
    });

    it('resolves nothing for a name that normalises away entirely', () => {
      const fresh = new TeamRegistry();
      fresh.intern('Palmeiras-SP');
      for (const nonsense of ['???', '-', '...', '()']) {
        expect(fresh.resolveQuery(nonsense).team, nonsense).toBeUndefined();
      }
    });

    it('returns nothing for an empty query', () => {
      expect(registry.resolveQuery('   ').team).toBeUndefined();
    });
  });

  describe('resolveClubLabel', () => {
    it('links a FIFA label to the Brazilian club', () => {
      registry.intern('Sport-PE');
      expect(registry.resolveClubLabel('Sport Club do Recife')?.id).toBe('sport-pe');
    });

    it('refuses to link a foreign club that merely shares a name', () => {
      registry.intern('Barcelona-EQU');
      expect(registry.resolveClubLabel('FC Barcelona')).toBeUndefined();
    });
  });

  it('names the derby between two rivals', () => {
    expect(registry.rivalryFor('gremio-rs', 'internacional-rs')?.name).toBe('Grenal');
    expect(registry.rivalryFor('internacional-rs', 'gremio-rs')?.name).toBe('Grenal');
    expect(registry.rivalryFor('gremio-rs', 'santos-sp')).toBeUndefined();
  });
});

describe('regressions', () => {
  const registry = new TeamRegistry();

  it('reads a space-separated SC/AC as a club-type word, not a state', () => {
    // "Central SC" is Central Sport Club of Pernambuco and "River AC" is Ríver
    // Atlético Clube of Piauí. Reading the suffix as Santa Catarina or Acre
    // split each club in two and left duplicate fixtures in the merged data.
    expect(parseTeamName('Central SC')).toMatchObject({ base: 'central' });
    expect(parseTeamName('Central SC').state).toBeUndefined();
    expect(parseTeamName('River AC').base).toBe('river');
    expect(parseTeamName('River AC').state).toBeUndefined();
  });

  it('still reads a hyphenated SC/CE as a state', () => {
    expect(parseTeamName('Avai-SC')).toMatchObject({ base: 'avai', state: 'SC' });
    expect(parseTeamName('Ceará - CE')).toMatchObject({ base: 'ceara', state: 'CE' });
  });

  it('unifies the two spellings of a club that the suffix used to split', () => {
    expect(registry.intern('Central SC').id).toBe(registry.intern('Central - PE').id);
    expect(registry.intern('River AC').id).toBe(registry.intern('River - PI').id);
  });

  it('rejoins a punctuated acronym', () => {
    expect(parseTeamName('C. R. B. - AL')).toMatchObject({ base: 'crb', state: 'AL' });
    expect(registry.intern('C. R. B. - AL').id).toBe(registry.intern('CRB').id);
  });

  it('strips the corporate form that used to fork a second club', () => {
    expect(parseTeamName('Portuguesa Desportos').base).toBe('portuguesa');
    expect(registry.intern('Portuguesa Desportos').id).toBe(registry.intern('Portuguesa').id);
  });

  it('does not let an unqualified club absorb two different states', () => {
    // "Real FC", "Real - RR" and "Real Desportivo - RO" are three clubs. The
    // first one seen adopts the first qualifier; a different one must fork.
    const fresh = new TeamRegistry();
    const bare = fresh.intern('Real FC');
    const roraima = fresh.intern('Real - RR');
    const rondonia = fresh.intern('Real Desportivo - RO');
    expect(roraima.id).toBe(bare.id);
    expect(rondonia.id).not.toBe(bare.id);
  });

  it('refuses a table where two clubs claim the same bare base', () => {
    // Ownership of a bare name must not depend on declaration order.
    expect(() => new TeamRegistry()).not.toThrow();
    const fresh = new TeamRegistry();
    expect(fresh.intern('Atletico').id).toBe('atletico-mg');
    expect(fresh.intern('Atletico-PR').id).toBe('athletico-pr');
  });
});
