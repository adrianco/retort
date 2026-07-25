/**
 * The tool catalogue.
 *
 * Ordered roughly by how a conversation tends to flow: find out what is in the
 * data, look up matches, then teams, then players, then competitions and
 * statistics.
 */

import type { ToolDefinition } from './types.js';
import { findDerbies, headToHeadTool, searchMatches } from './matchTools.js';
import { listTeams, teamProfileTool, teamRankings, teamStatsTool } from './teamTools.js';
import { clubSquad, playerProfileTool, searchPlayersTool } from './playerTools.js';
import {
  competitionBracket,
  competitionStandings,
  datasetInfo,
  listSeasons,
} from './competitionTools.js';
import { matchStatistics, recordExtremes, seasonComparison } from './statsTools.js';

export const TOOLS: ToolDefinition[] = [
  datasetInfo,
  listSeasons,
  listTeams,
  searchMatches,
  headToHeadTool,
  findDerbies,
  teamStatsTool,
  teamProfileTool,
  teamRankings,
  searchPlayersTool,
  playerProfileTool,
  clubSquad,
  competitionStandings,
  competitionBracket,
  matchStatistics,
  recordExtremes,
  seasonComparison,
] as ToolDefinition[];

export function toolByName(name: string): ToolDefinition | undefined {
  return TOOLS.find((tool) => tool.name === name);
}

export type { ToolDefinition, ToolResult } from './types.js';
