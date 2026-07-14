import { beforeAll, describe, expect, it } from "vitest";
import type { SoccerDataStore } from "../src/data/store.js";
import { loadTestStore } from "./support/testStore.js";

describe("SoccerDataStore", () => {
  let store: SoccerDataStore;

  beforeAll(async () => {
    store = await loadTestStore();
  });

  it("test_given_all_six_source_files_when_loaded_then_matches_and_players_are_present", () => {
    // Given the six provided Kaggle CSV files
    // When the store loads them all
    // Then both match and player data are non-empty
    expect(store.matches.length).toBeGreaterThan(0);
    expect(store.players.length).toBeGreaterThan(0);
  });

  it("test_given_all_fifa_rows_when_loaded_then_every_player_row_is_kept", () => {
    // Given fifa_data.csv has 18,207 player rows
    // When the store loads the file
    // Then every player row is present (no accidental drops)
    expect(store.players.length).toBe(18207);
  });

  it("test_given_overlapping_brasileirao_sources_when_loaded_then_a_season_is_not_double_counted", () => {
    // Given Brasileirao_Matches.csv and novo_campeonato_brasileiro.csv both independently
    // cover full 2012-2019 seasons (380 matches per season each)
    // When the store loads both files
    const matches2019 = store.matches.filter((m) => m.competition === "Brasileirao" && m.season === 2019);
    // Then the season appears once (380 matches), not twice (760)
    expect(matches2019.length).toBe(380);
  });

  it("test_given_overlapping_copa_do_brasil_sources_when_loaded_then_a_season_is_not_double_counted", () => {
    // Given Brazilian_Cup_Matches.csv and BR-Football-Dataset.csv both cover 2016 Copa do Brasil matches
    // When the store loads both files
    const matches2016 = store.matches.filter((m) => m.competition === "CopaDoBrasil" && m.season === 2016);
    // Then the primary source's count (162) is used rather than a doubled total
    expect(matches2016.length).toBe(162);
  });

  it("test_given_a_club_present_in_both_match_and_player_data_when_looked_up_by_key_then_both_link_to_the_same_team_key", () => {
    // Given Grêmio appears in both match data (as "Gremio" without accents) and FIFA player data (as "Grêmio")
    const matches = store.matchesForTeamKey("gremio");
    const players = store.playersForClubKey("gremio");
    // When looking both up by the shared normalized key
    // Then both non-trivial result sets are found under the same key
    expect(matches.length).toBeGreaterThan(0);
    expect(players.length).toBeGreaterThan(0);
  });

  it("test_given_a_row_with_an_unparseable_date_when_loaded_then_the_match_is_kept_with_a_null_date", () => {
    // Given Libertadores_Matches.csv contains at least one row with datetime "NA"
    // When the store loads it
    const unparsed = store.matches.filter((m) => m.date === null);
    // Then the row is retained (not silently dropped) with a null date rather than throwing
    expect(unparsed.length).toBeGreaterThan(0);
  });
});
