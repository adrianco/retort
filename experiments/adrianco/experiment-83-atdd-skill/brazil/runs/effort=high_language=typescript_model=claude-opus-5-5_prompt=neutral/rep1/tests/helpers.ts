import { getDataset } from "../src/data.js";
import { SoccerQueries } from "../src/query.js";
import { runTool } from "../src/tools.js";

let q: SoccerQueries | undefined;
export function queries(): SoccerQueries {
  return (q ??= new SoccerQueries(getDataset()));
}

export function ask(tool: string, args: Record<string, unknown> = {}): string {
  return runTool(queries(), tool, args);
}
