/**
 * Acceptance: the server speaks MCP and advertises the documented capabilities.
 */
import { describe, it, expect, afterEach, beforeEach } from 'vitest';
import { startSystem, type TestSystem } from './harness.js';

let sys: TestSystem;
beforeEach(async () => { sys = await startSystem(); });
afterEach(async () => { await sys.close(); });

describe('MCP protocol surface', () => {
  it('exposes a tool for each required query category', async () => {
    const tools = await sys.listTools();
    expect(tools).toEqual(expect.arrayContaining([
      'find_matches',
      'head_to_head',
      'team_record',
      'find_players',
      'competition_standings',
      'competition_statistics',
    ]));
  });

  it('reports a friendly error when a required argument is missing', async () => {
    const res = await sys.callRaw('team_record', {});
    expect(res.isError).toBe(true);
  });
});
