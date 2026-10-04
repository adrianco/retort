/**
 * Shared test fixtures: one knowledge base and one connected MCP client per
 * test file (loading all six CSVs takes well under a second).
 */
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { SoccerKnowledgeBase } from "../src/queries.js";
import { createServer } from "../src/server.js";

let kb: SoccerKnowledgeBase | undefined;

export function getKb(): SoccerKnowledgeBase {
  kb ??= SoccerKnowledgeBase.load();
  return kb;
}

export async function connectClient(): Promise<Client> {
  const server = createServer(getKb());
  const [serverTransport, clientTransport] = InMemoryTransport.createLinkedPair();
  await server.connect(serverTransport);
  const client = new Client({ name: "test-client", version: "1.0.0" });
  await client.connect(clientTransport);
  return client;
}

export interface ToolText {
  text: string;
  isError: boolean;
  ms: number;
}

export async function callTool(client: Client, name: string, args: Record<string, unknown> = {}): Promise<ToolText> {
  const t0 = performance.now();
  const res = (await client.callTool({ name, arguments: args })) as { content: { type: string; text: string }[]; isError?: boolean };
  return { text: res.content.map((c) => c.text).join("\n"), isError: Boolean(res.isError), ms: performance.now() - t0 };
}
