/**
 * Tool definition shape.
 *
 * Tools are declared independently of the MCP transport: each is a Zod schema
 * plus a pure `(graph, input) -> { text, data }` function. `server.ts` adapts
 * them to the SDK, and the tests call them directly, so the behaviour under
 * test is exactly the behaviour a client gets.
 */

import type { z } from 'zod';
import type { SoccerGraph } from '../graph/graph.js';

export interface ToolResult {
  /** Human-readable answer, returned as the tool's text content. */
  text: string;
  /** Structured payload, returned alongside the text for programmatic use. */
  data: Record<string, unknown>;
}

export interface ToolDefinition<Shape extends z.ZodRawShape = z.ZodRawShape> {
  name: string;
  title: string;
  description: string;
  schema: z.ZodObject<Shape>;
  handler: (graph: SoccerGraph, input: z.infer<z.ZodObject<Shape>>) => ToolResult;
}

/** Helper that keeps the schema and handler types tied together. */
export function defineTool<Shape extends z.ZodRawShape>(
  definition: ToolDefinition<Shape>,
): ToolDefinition<Shape> {
  return definition;
}
