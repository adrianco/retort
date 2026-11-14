import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { loadDataset } from '../src/data.js';
import { SoccerDB } from '../src/queries.js';
import { createServer } from '../src/server.js';

let db: SoccerDB | undefined;
/** Given the match and player data is loaded (once per test file). */
export function givenDataIsLoaded(): SoccerDB {
  return (db ??= new SoccerDB(loadDataset()));
}

export async function connectClient(): Promise<{ ask: (tool: string, args?: Record<string, unknown>) => Promise<{ text: string; isError: boolean }>; client: Client }> {
  const [a, b] = InMemoryTransport.createLinkedPair();
  await createServer(givenDataIsLoaded()).connect(a);
  const client = new Client({ name: 'test-client', version: '1.0.0' });
  await client.connect(b);
  const ask = async (tool: string, args: Record<string, unknown> = {}) => {
    const r = await client.callTool({ name: tool, arguments: args });
    const content = r.content as { type: string; text: string }[];
    return { text: content.map((c) => c.text).join('\n'), isError: r.isError === true };
  };
  return { ask, client };
}
