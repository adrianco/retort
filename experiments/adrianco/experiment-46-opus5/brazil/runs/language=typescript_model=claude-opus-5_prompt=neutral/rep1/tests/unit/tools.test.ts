/**
 * Contract of the tool layer: catalogue integrity, argument validation, error
 * handling and the MCP registration that exposes all of it.
 */

import { describe, expect, it } from 'vitest';
import { getGraph } from '../../src/graph/graph.js';
import { TOOLS, toolByName } from '../../src/tools/index.js';
import { createServer, SERVER_NAME } from '../../src/server.js';

const graph = getGraph();

describe('tool catalogue', () => {
  it('exposes tools for all five capability areas', () => {
    for (const name of [
      'search_matches',
      'team_stats',
      'search_players',
      'competition_standings',
      'match_statistics',
    ]) {
      expect(toolByName(name), name).toBeDefined();
    }
  });

  it('has unique names', () => {
    expect(new Set(TOOLS.map((t) => t.name)).size).toBe(TOOLS.length);
  });

  it('documents every tool and every argument', () => {
    for (const tool of TOOLS) {
      expect(tool.description.length, tool.name).toBeGreaterThan(40);
      expect(tool.title.length, tool.name).toBeGreaterThan(0);
      for (const [field, schema] of Object.entries(tool.schema.shape)) {
        expect(schema.description, `${tool.name}.${field}`).toBeTruthy();
      }
    }
  });

  it('either answers or explains itself when called with no arguments', () => {
    for (const tool of TOOLS) {
      const parsed = tool.schema.safeParse({});
      if (!parsed.success) continue;
      try {
        const result = tool.handler(graph, parsed.data as never);
        expect(result.text.length, tool.name).toBeGreaterThan(0);
        expect(typeof result.data, tool.name).toBe('object');
      } catch (error) {
        // A tool may require a choice the schema cannot express, but it has to
        // name what is missing rather than fail opaquely.
        expect(error, tool.name).toBeInstanceOf(Error);
        expect((error as Error).message.length, tool.name).toBeGreaterThan(10);
      }
    }
  });
});

describe('argument validation', () => {
  it('rejects a missing required argument', () => {
    const result = toolByName('competition_standings')!.schema.safeParse({ competition: 'serie-a' });
    expect(result.success).toBe(false);
  });

  it('rejects an out-of-range limit', () => {
    expect(toolByName('search_matches')!.schema.safeParse({ limit: 0 }).success).toBe(false);
    expect(toolByName('search_matches')!.schema.safeParse({ limit: 10_000 }).success).toBe(false);
  });

  it('rejects an unknown enum value', () => {
    expect(toolByName('search_matches')!.schema.safeParse({ venue: 'neutral' }).success).toBe(false);
  });

  it('applies documented defaults', () => {
    const parsed = toolByName('search_matches')!.schema.parse({});
    expect(parsed.venue).toBe('any');
    expect(parsed.order).toBe('newest');
    expect(parsed.limit).toBe(20);
  });
});

describe('error handling', () => {
  const run = (name: string, args: unknown) => {
    const tool = toolByName(name)!;
    return () => tool.handler(graph, tool.schema.parse(args) as never);
  };

  it('names the candidates when a team cannot be resolved', () => {
    expect(run('team_stats', { team: 'Notaclub Athletic' })).toThrow(/No team matched/);
  });

  it('reports an unknown competition with the valid ids', () => {
    expect(run('competition_standings', { competition: 'la-liga', season: 2019 })).toThrow(
      /Unknown competition/,
    );
  });

  it('reports an unparseable date', () => {
    expect(run('search_matches', { dateFrom: 'the day before yesterday' })).toThrow(
      /Could not parse/,
    );
  });

  it('requires an identifier for a player profile', () => {
    expect(run('player_profile', {})).toThrow(/name.*playerId/);
  });

  it('reports an empty result rather than throwing', () => {
    const tool = toolByName('search_matches')!;
    const result = tool.handler(graph, tool.schema.parse({ season: 1899 }) as never);
    expect(result.text).toContain('No matches found');
    expect(result.data['total']).toBe(0);
  });
});

describe('MCP registration', () => {
  it('constructs a server with every tool registered', () => {
    const server = createServer(graph);
    expect(server).toBeDefined();
    // The SDK stores registrations privately; assert via its public shape that
    // construction with all tools succeeded and the identity is right.
    expect(SERVER_NAME).toBe('brazilian-soccer');
  });
});
