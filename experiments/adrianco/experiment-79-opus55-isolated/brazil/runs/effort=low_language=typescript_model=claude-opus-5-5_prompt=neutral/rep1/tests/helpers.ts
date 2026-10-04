import { SoccerKB } from '../src/queries.js';
import { callTool } from '../src/tools.js';

/** Given the match and player data is loaded (once per test file). */
export const kb = new SoccerKB();
export const ask = (tool: string, args: Record<string, unknown> = {}) => callTool(kb, tool, args);
