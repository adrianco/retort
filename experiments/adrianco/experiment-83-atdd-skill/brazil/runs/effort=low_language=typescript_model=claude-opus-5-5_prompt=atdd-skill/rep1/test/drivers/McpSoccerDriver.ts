import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { expect } from "vitest";
import path from "node:path";

// Protocol driver: the only layer that knows the system is an MCP server over stdio.
export class McpSoccerDriver {
  private client?: Client;
  private lastAnswer = "";

  async connect() {
    const root = path.resolve(import.meta.dirname, "../..");
    const transport = new StdioClientTransport({
      command: process.execPath,
      args: [path.join(root, "node_modules/tsx/dist/cli.mjs"), path.join(root, "src/index.ts")],
      cwd: root,
    });
    this.client = new Client({ name: "acceptance-tests", version: "1.0.0" });
    await this.client.connect(transport);
  }

  async disconnect() { await this.client?.close(); }

  async ask(tool: string, args: Record<string, unknown>): Promise<string> {
    const clean = Object.fromEntries(Object.entries(args).filter(([, v]) => v !== undefined));
    const result = await this.client!.callTool({ name: tool, arguments: clean });
    const text = (result.content as { type: string; text: string }[]).map(c => c.text).join("\n");
    if (result.isError) throw new Error(`Query ${tool} failed: ${text}`);
    this.lastAnswer = text;
    return text;
  }

  private matchLines(text = this.lastAnswer) { return text.split("\n").filter(l => /^\s*(- |\d+\. )\d{4}-\d{2}-\d{2}/.test(l)); }

  assertMatchesListed(atLeast: number) {
    expect(this.matchLines().length, `expected ≥${atLeast} matches in:\n${this.lastAnswer}`).toBeGreaterThanOrEqual(atLeast);
  }
  assertPlayersListed(atLeast: number) {
    const players = this.lastAnswer.split("\n").filter(l => /^\d+\. .+Overall: \d+/.test(l));
    expect(players.length, this.lastAnswer).toBeGreaterThanOrEqual(atLeast);
  }
  assertMentions(phrases: string[]) {
    for (const p of phrases) expect(this.lastAnswer.toLowerCase()).toContain(p.toLowerCase());
  }
  assertHasScore() { expect(this.lastAnswer).toMatch(/\d+-\d+/); }
  assertRecordMatches(matches: number) { expect(this.lastAnswer).toMatch(new RegExp(`Matches: ${matches}\\b`)); }
  assertTopPlayer(name: string) { expect(this.lastAnswer).toMatch(new RegExp(`^1\\. ${name} - Overall`, "m")); }
  assertChampion(team: string, points?: number) {
    const first = this.lastAnswer.split("\n").find(l => l.startsWith("1. ")) ?? "";
    expect(first).toContain(team);
    if (points !== undefined) expect(first).toContain(`${points} pts`);
  }
  assertRelegatedCount(n: number) {
    const line = this.lastAnswer.split("\n").find(l => l.startsWith("Relegated:")) ?? "";
    expect(line.replace("Relegated:", "").split(",").filter(s => s.trim()).length).toBe(n);
  }
  async assertSameMatchCount(a: string, b: string) {
    const countA = this.matchLines(await this.ask("search_matches", { team: a, limit: 10000 })).length;
    const countB = this.matchLines(await this.ask("search_matches", { team: b, limit: 10000 })).length;
    expect(countA).toBeGreaterThan(0);
    expect(countA).toBe(countB);
  }
  async assertDatasetsLoaded(count: number) {
    const text = await this.ask("dataset_info", {});
    const loaded = text.split("\n").filter(l => /^- .+\.csv: [1-9]\d* rows/.test(l));
    expect(loaded.length, text).toBe(count);
  }
  assertElapsed(elapsed: number, limit: number) { expect(elapsed).toBeLessThan(limit); }
}
