/**
 * Executable specification: finding players and squads.
 *
 * Layer 1 (test cases) — domain language only.
 */
import { spec } from './dsl/spec.js';

spec('should find a player by name', async ({ given, players }) => {
  given.player({ name: 'Gabriel Barbosa', club: 'Flamengo', nationality: 'Brazil', overall: 82, position: 'ST' });
  given.player({ name: 'Gabriel Jesus', club: 'Manchester City', nationality: 'Brazil' });

  await players.lookUp({ name: 'Gabriel Barbosa' });

  players.confirmPlayer({ name: 'Gabriel Barbosa', club: 'Flamengo', overall: 82, position: 'ST' });
});

spec('should find a player whether or not the name is typed with accents', async ({ given, players }) => {
  given.player({ name: 'Éverton Ribeiro', club: 'Flamengo' });

  await players.lookUp({ name: 'everton ribeiro' });

  players.confirmPlayer({ name: 'Éverton Ribeiro' });
});

spec("should describe a player's skills", async ({ given, players }) => {
  given.player({ name: 'Bruno Henrique', finishing: 81, dribbling: 84, sprintSpeed: 92 });

  await players.lookUp({ name: 'Bruno Henrique' });

  players.confirmSkills({ finishing: 81, dribbling: 84, sprintSpeed: 92 });
});

spec('should say so when a player is not in the data, suggesting similar names', async ({ given, players }) => {
  given.player({ name: 'Gabriel Jesus' });

  await players.lookUp({ name: 'Gabriel Barbosa' });

  players.confirmNotFound({ suggesting: 'Gabriel Jesus' });
});

spec('should list the players of a nationality, best rated first', async ({ given, players }) => {
  given.player({ name: 'Neymar Jr', nationality: 'Brazil', overall: 92, club: 'Paris Saint-Germain' });
  given.player({ name: 'Casemiro', nationality: 'Brazil', overall: 89, club: 'Real Madrid' });
  given.player({ name: 'L. Messi', nationality: 'Argentina', overall: 94, club: 'FC Barcelona' });
  given.player({ name: 'Alisson', nationality: 'Brazil', overall: 89, club: 'Liverpool' });

  await players.search({ nationality: 'Brazil' });

  players.confirmListed(['Neymar Jr', 'Alisson', 'Casemiro']);
});

spec('should list the players at a club, whichever way the club is written', async ({ given, players }) => {
  given.player({ name: 'Ricardo Oliveira', club: 'Atlético Mineiro', overall: 77 });
  given.player({ name: 'Cazares', club: 'Atlético Mineiro', overall: 78 });
  given.player({ name: 'Diego Godín', club: 'Atlético Madrid', overall: 90 });

  await players.search({ club: 'Atletico-MG' });

  players.confirmListed(['Cazares', 'Ricardo Oliveira']);
});

spec('should find the forwards at a club', async ({ given, players }) => {
  given.player({ name: 'Diego Souza', club: 'São Paulo', position: 'ST' });
  given.player({ name: 'Everton', club: 'São Paulo', position: 'LW' });
  given.player({ name: 'Arboleda', club: 'São Paulo', position: 'CB' });
  given.player({ name: 'Sidão', club: 'São Paulo', position: 'GK' });
  given.player({ name: 'Rodrigo Caio', club: 'Flamengo', position: 'ST' });

  await players.search({ club: 'São Paulo FC', position: 'forward' });

  players.confirmListed(['Diego Souza', 'Everton'], { inAnyOrder: true });
});

spec('should summarise the Brazilian players at Brazilian clubs', async ({ given, players }) => {
  given.match({ home: 'Flamengo-RJ', away: 'Palmeiras-SP' });
  given.player({ name: 'Diego', club: 'Flamengo', nationality: 'Brazil', overall: 78 });
  given.player({ name: 'Vinícius Júnior', club: 'Flamengo', nationality: 'Brazil', overall: 70 });
  given.player({ name: 'Mancuello', club: 'Flamengo', nationality: 'Argentina', overall: 75 });
  given.player({ name: 'Dudu', club: 'Palmeiras', nationality: 'Brazil', overall: 72 });
  given.player({ name: 'Neymar Jr', club: 'Paris Saint-Germain', nationality: 'Brazil', overall: 92 });

  await players.summariseByBrazilianClub({ nationality: 'Brazil' });

  players.confirmClubSummary({ club: 'Flamengo', players: 2, averageRating: 74 });
  players.confirmClubSummary({ club: 'Palmeiras', players: 1, averageRating: 72 });
  players.confirmClubNotInSummary('Paris Saint-Germain');
});
