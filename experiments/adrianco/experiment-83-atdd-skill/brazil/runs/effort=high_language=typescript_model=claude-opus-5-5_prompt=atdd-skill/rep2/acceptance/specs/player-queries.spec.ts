/**
 * Executable specification: finding players and their ratings.
 */
import { describe, it } from 'vitest';
import { useSoccerDsl } from '../dsl/soccer-dsl.js';

describe('Player queries', () => {
  const { given, players } = useSoccerDsl();

  it('should describe a player found by name', async () => {
    await given.player({ name: 'Gabriel Barbosa', club: 'Santos', position: 'ST', overall: 78, age: 22 });

    await players.confirmProfile({ name: 'gabriel barbosa', club: 'Santos', position: 'ST', overall: 78, nationality: 'Brazil' });
  });

  it('should suggest similar names when a player is not in the data', async () => {
    await given.player({ name: 'Gabriel Jesus', club: 'Manchester City', overall: 83 });
    await given.player({ name: 'Rodrygo', club: 'Santos', overall: 74 });

    await players.confirmUnknown({ name: 'Gabriel Barbosa', suggesting: ['Gabriel Jesus'] });
  });

  it('should rank Brazilian players by overall rating', async () => {
    await given.player({ name: 'Alisson', club: 'Liverpool', position: 'GK', overall: 89 });
    await given.player({ name: 'Neymar Jr', club: 'Paris Saint-Germain', position: 'LW', overall: 92 });
    await given.player({ name: 'L. Messi', nationality: 'Argentina', club: 'FC Barcelona', overall: 94 });
    await given.player({ name: 'Casemiro', club: 'Real Madrid', position: 'CDM', overall: 88 });

    await players.confirmFound({ nationality: 'Brazilian', expected: ['Neymar Jr', 'Alisson', 'Casemiro'] });
  });

  it('should list the highest rated players at a club', async () => {
    await given.player({ name: 'Fábio', club: 'Cruzeiro', position: 'GK', overall: 78 });
    await given.player({ name: 'Thiago Neves', club: 'Cruzeiro', position: 'CAM', overall: 80 });
    await given.player({ name: 'Everton', club: 'Grêmio', overall: 82 });

    await players.confirmFound({ club: 'Cruzeiro', expected: ['Thiago Neves', 'Fábio'] });
  });

  it('should find the forwards at a club', async () => {
    await given.player({ name: 'Diego Souza', club: 'São Paulo', position: 'ST', overall: 77 });
    await given.player({ name: 'Everton', club: 'São Paulo', position: 'LW', overall: 76 });
    await given.player({ name: 'Hudson', club: 'São Paulo', position: 'CDM', overall: 74 });

    await players.confirmFound({ club: 'Sao Paulo FC', position: 'forward', expected: ['Diego Souza', 'Everton'] });
  });

  it('should summarise Brazilian players at Brazilian clubs', async () => {
    await given.brasileiraoMatch({ home: 'Santos', away: 'Grêmio' });
    await given.player({ name: 'Rodrygo', club: 'Santos', overall: 74 });
    await given.player({ name: 'Gabriel', club: 'Santos', overall: 70 });
    await given.player({ name: 'Bruno Cortez', club: 'Grêmio', overall: 73 });
    await given.player({ name: 'Paulinho', club: 'FC Barcelona', overall: 82 });
    await given.player({ name: 'Bryan Ruiz', nationality: 'Costa Rica', club: 'Santos', overall: 75 });

    await players.confirmClubSummary({
      nationality: 'Brazil',
      clubs: [
        { club: 'Santos', players: 2, averageOverall: 72 },
        { club: 'Grêmio', players: 1, averageOverall: 73 },
      ],
    });
  });

  it('should say so when no player matches', async () => {
    await given.player({ name: 'Neymar Jr', club: 'Paris Saint-Germain', overall: 92 });

    await players.confirmNoneFound({ club: 'Flamengo' });
  });
});
