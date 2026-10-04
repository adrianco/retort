/**
 * Performance requirements: simple lookups < 2 s, aggregate queries < 5 s.
 * (In practice they take a few milliseconds once data is loaded.)
 */
import { describe, expect, it } from "vitest";
import { loadDataset } from "../src/data.js";
import { ask } from "./helpers.js";

const time = (fn: () => unknown) => {
  const t0 = performance.now();
  fn();
  return performance.now() - t0;
};

describe("query performance", () => {
  it("cold-loads every dataset well under the aggregate budget", () => {
    expect(time(() => loadDataset())).toBeLessThan(5000);
  });

  it.each([
    ["search_matches", { team: "Flamengo", opponent: "Corinthians", limit: 1 }],
    ["get_player", { name: "Neymar" }],
    ["search_players", { club: "Santos" }],
    ["find_team", { query: "Atletico" }],
  ])("simple lookup %s < 2s", (tool, args) => {
    ask("dataset_info");
    expect(time(() => ask(tool, args))).toBeLessThan(2000);
  });

  it.each([
    ["match_statistics", {}],
    ["team_rankings", { metric: "home_win_rate" }],
    ["biggest_wins", { limit: 50 }],
    ["compare_seasons", { seasons: [2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023] }],
    ["cup_finals", { competition: "copa do brasil" }],
    ["club_player_summary", { nationality: "Brazil" }],
  ])("aggregate query %s < 5s", (tool, args) => {
    expect(time(() => ask(tool, args))).toBeLessThan(5000);
  });
});
