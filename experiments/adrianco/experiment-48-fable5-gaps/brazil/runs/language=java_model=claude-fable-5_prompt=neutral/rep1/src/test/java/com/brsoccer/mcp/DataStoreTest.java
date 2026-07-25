package com.brsoccer.mcp;

import com.brsoccer.mcp.data.DataStore;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Success criterion: all 6 CSV files are loadable and queryable. */
class DataStoreTest {

    @Test
    void allSixFilesLoad() {
        DataStore s = TestData.store();
        // 4,180 rows minus 82 postponed/canceled fixtures whose goals are "NA"
        assertEquals(4098, s.sourceCounts().get("Brasileirao_Matches.csv"));
        assertTrue(s.sourceCounts().get("novo_campeonato_brasileiro.csv") > 2000,
            "historical file should contribute the 2003-2011 seasons at minimum");
        // 1,337 rows minus 16 fixtures with "NA" scores (2021 tournament was cut off mid-season)
        assertEquals(1321, s.sourceCounts().get("Brazilian_Cup_Matches.csv"));
        assertTrue(s.sourceCounts().get("Libertadores_Matches.csv") >= 1240);
        assertTrue(s.sourceCounts().get("BR-Football-Dataset.csv") > 4000);
        assertEquals(18207, s.players().size());
    }

    @Test
    void duplicateMatchesAcrossFilesAreMerged() {
        DataStore s = TestData.store();
        // novo_campeonato covers 2003-2019; Brasileirao_Matches covers 2012-2022 -> heavy overlap
        assertTrue(s.duplicatesMerged() > 2000, "expected overlap seasons to be de-duplicated, got "
            + s.duplicatesMerged());
    }

    @Test
    void matchesAreSortedAndWellFormed() {
        DataStore s = TestData.store();
        var ms = s.matches();
        assertTrue(ms.size() > 15000);
        for (int i = 1; i < ms.size(); i++) {
            assertTrue(!ms.get(i).date.isBefore(ms.get(i - 1).date));
        }
        for (var m : ms) {
            assertTrue(m.homeGoals >= 0 && m.awayGoals >= 0);
            assertTrue(m.homeKey != null && m.awayKey != null);
        }
    }

    @Test
    void utf8NamesSurviveLoading() {
        DataStore s = TestData.store();
        assertTrue(s.matches().stream().anyMatch(m ->
            m.homeRaw.contains("Grêmio") || m.awayRaw.contains("Grêmio")));
        assertTrue(s.players().stream().anyMatch(p -> p.name.contains("é") || p.name.contains("ã")));
    }
}
