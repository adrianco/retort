import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { loadDataset } from "../src/loader.js";
import type { Dataset } from "../src/types.js";

const DATA_DIR = join(dirname(fileURLToPath(import.meta.url)), "..", "data", "kaggle");

let cached: Dataset | null = null;

/** Load the dataset once per test process. */
export function dataset(): Dataset {
  if (!cached) cached = loadDataset(DATA_DIR);
  return cached;
}

export { DATA_DIR };
