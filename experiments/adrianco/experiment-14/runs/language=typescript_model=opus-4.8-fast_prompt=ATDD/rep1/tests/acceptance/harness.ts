/**
 * Acceptance-test harness.
 *
 * Spins up the real MCP server in-process and connects a real MCP client to it
 * over a linked in-memory transport pair. Tests therefore exercise the System
 * Under Test ONLY through the public MCP protocol (tools/list, tools/call) with
 * no back-door access to internals.
 *
 * The one thing tests are allowed to touch directly is the DataStore used to
 * seed data — that is the system's "database". Each test constructs its own
 * empty store, making every scenario atomic and independent.
 */
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { DataStore } from '../../src/data/store.js';
import { createSoccerServer } from '../../src/server.js';

export interface TestSystem {
  store: DataStore;
  /** Call an MCP tool and return its structured JSON result. */
  call(tool: string, args?: Record<string, unknown>): Promise<any>;
  /** Raw tool call returning the full MCP result (for error-path assertions). */
  callRaw(tool: string, args?: Record<string, unknown>): Promise<any>;
  listTools(): Promise<string[]>;
  close(): Promise<void>;
}

/** Start a fresh, empty running system and return a client bound to it. */
export async function startSystem(): Promise<TestSystem> {
  const store = new DataStore();
  const server = createSoccerServer(store);

  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  const client = new Client({ name: 'acceptance-test', version: '1.0.0' });

  await Promise.all([
    server.connect(serverTransport),
    client.connect(clientTransport),
  ]);

  const callRaw = async (tool: string, args: Record<string, unknown> = {}) =>
    client.callTool({ name: tool, arguments: args });

  return {
    store,
    callRaw,
    async call(tool, args = {}) {
      const res: any = await callRaw(tool, args);
      if (res.isError) {
        const text = res.content?.map((c: any) => c.text).join('\n');
        throw new Error(`Tool ${tool} returned error: ${text}`);
      }
      // Prefer structuredContent; fall back to parsing the text payload.
      if (res.structuredContent) return res.structuredContent;
      const text = res.content?.find((c: any) => c.type === 'text')?.text ?? '{}';
      return JSON.parse(text);
    },
    async listTools() {
      const res = await client.listTools();
      return res.tools.map((t) => t.name);
    },
    async close() {
      await client.close();
      await server.close();
    },
  };
}
