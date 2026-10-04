/** Parses "2-1" style scores (also used for corners and shots) into a pair of numbers. */
export function parseScore(score: string): [number, number] {
  const match = /^\s*(\d+)\s*-\s*(\d+)\s*$/.exec(score);
  if (!match) throw new Error(`"${score}" is not a score like "2-1"`);
  return [Number(match[1]), Number(match[2])];
}
