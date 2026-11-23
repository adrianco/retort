import { createInterface } from "node:readline";
import { fileURLToPath } from "node:url";
import { Graph } from "./data.js";
import { query, tools } from "./queries.js";

const graph = new Graph(
  fileURLToPath(new URL("../data/kaggle/", import.meta.url)),
);
function respond(line: string) {
  const error = (id: unknown, code: number, message: string) => ({
    jsonrpc: "2.0",
    id,
    error: { code, message },
  });
  let req;
  try {
    req = JSON.parse(line);
  } catch {
    return error(null, -32700, "Parse error");
  }
  if (req?.jsonrpc !== "2.0" || typeof req.method !== "string")
    return error(req?.id ?? null, -32600, "Invalid request");
  if (req.id === undefined) return;
  let result;
  switch (req.method) {
    case "initialize":
      result = {
        protocolVersion: "2025-06-18",
        capabilities: { tools: {} },
        serverInfo: { name: "brazilian-soccer", version: "1.0.0" },
        instructions:
          "Use the tools for questions about the local datasets. Join player club and match team across calls. Results can cover partial seasons. Individual match scorers are unavailable. Records rank by points, wins, goal difference, then goals scored. Derby filter covers selected traditional rivalries.",
      };
      break;
    case "ping":
      result = {};
      break;
    case "tools/list":
      result = { tools };
      break;
    case "tools/call":
      if (typeof req.params?.name !== "string")
        return error(req.id, -32602, "Missing tool name");
      try {
        result = {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                query(graph, req.params.name, req.params.arguments),
                null,
                2,
              ),
            },
          ],
        };
      } catch (e) {
        result = {
          isError: true,
          content: [{ type: "text", text: (e as Error).message }],
        };
      }
      break;
    default:
      return error(req.id, -32601, "Method not found");
  }
  return { jsonrpc: "2.0", id: req.id, result };
}
for await (const line of createInterface({
  input: process.stdin,
  crlfDelay: Infinity,
})) {
  const response = respond(line);
  if (response) process.stdout.write(JSON.stringify(response) + "\n");
}
