import type { Match, Player } from "./types.js";
import { defaultDataDir, loadAll } from "./loaders.js";

export class DataStore {
  matches: Match[] = [];
  players: Player[] = [];
  loaded = false;
  dataDir: string;

  constructor(dataDir?: string) {
    this.dataDir = dataDir ?? defaultDataDir();
  }

  load(): this {
    if (this.loaded) return this;
    const { matches, players } = loadAll(this.dataDir);
    this.matches = matches;
    this.players = players;
    this.loaded = true;
    return this;
  }
}

let singleton: DataStore | null = null;
export function getDataStore(dataDir?: string): DataStore {
  if (!singleton) singleton = new DataStore(dataDir).load();
  return singleton;
}

export function resetDataStore(): void {
  singleton = null;
}
