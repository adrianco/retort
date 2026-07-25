/**
 * Small collection helpers shared across the loading, graph and query layers.
 */

/** Append to a map of arrays, creating the bucket on first use. */
export function pushInto<K, V>(map: Map<K, V[]>, key: K, value: V): void {
  const bucket = map.get(key);
  if (bucket) bucket.push(value);
  else map.set(key, [value]);
}

/**
 * Group items by a derived key, preserving input order within each group.
 */
export function groupBy<K, V>(items: Iterable<V>, keyOf: (item: V) => K): Map<K, V[]> {
  const groups = new Map<K, V[]>();
  for (const item of items) pushInto(groups, keyOf(item), item);
  return groups;
}

/**
 * Ascending comparator for `YYYY-MM-DD` strings.
 *
 * Returns 0 for equal dates, so it is a valid total order and stable sorts stay
 * stable -- a two-branch `a < b ? -1 : 1` silently is not.
 */
export function byDateAscending(a: { date: string }, b: { date: string }): number {
  return a.date < b.date ? -1 : a.date > b.date ? 1 : 0;
}
