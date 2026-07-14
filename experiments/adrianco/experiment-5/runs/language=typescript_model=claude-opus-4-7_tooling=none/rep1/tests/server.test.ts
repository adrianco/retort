import { describe, it, expect, beforeAll } from 'vitest';
import { loadData } from '../src/loader';
import { createServer } from '../src/server';
import type { DataStore } from '../src/types';

let store: DataStore;

beforeAll(() => {
  store = loadData({ dataDir: 'data/kaggle' });
});

describe('MCP server setup', () => {
  it('creates a server with registered tools', () => {
    const server = createServer(store);
    expect(server).toBeDefined();
    expect(server.server).toBeDefined();
  });
});
