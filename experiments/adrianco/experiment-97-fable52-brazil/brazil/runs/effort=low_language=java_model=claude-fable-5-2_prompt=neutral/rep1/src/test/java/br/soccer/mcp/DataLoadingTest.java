package br.soccer.mcp;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Path;
import java.time.LocalDate;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

@DisplayName("Feature: Data loading")
class DataLoadingTest {
    private final DataStore ds = TestData.STORE;

    @Test
    @DisplayName("Scenario: all six CSV files are loaded with the documented row counts")
    void allFilesLoaded() {
        assertEquals(6886, ds.rowCounts.get(DataStore.F_HISTORICAL));
        assertEquals(4180, ds.rowCounts.get(DataStore.F_BRASILEIRAO));
        assertEquals(1337, ds.rowCounts.get(DataStore.F_CUP));
        // one of the 1,255 rows has neither a date nor a season and is dropped
        assertEquals(1254, ds.rowCounts.get(DataStore.F_LIBERTADORES));
        assertEquals(10296, ds.rowCounts.get(DataStore.F_EXTENDED));
        assertEquals(18207, ds.rowCounts.get(DataStore.F_FIFA));
    }

    @Test
    @DisplayName("Scenario: every match has teams, a competition and a season")
    void matchesAreWellFormed() {
        for (Match m : ds.matches) {
            assertNotNull(m.home);
            assertNotNull(m.away);
            assertTrue(DataStore.COMPETITIONS.contains(m.competition), m.competition);
            assertTrue(m.season >= 2003 && m.season <= 2023, "season " + m.season);
        }
    }

    @Test
    @DisplayName("Scenario: multiple date formats are parsed")
    void dateFormats() {
        assertEquals(LocalDate.of(2023, 9, 24), DataStore.parseDate("2023-09-24"));
        assertEquals(LocalDate.of(2003, 3, 29), DataStore.parseDate("29/03/2003"));
        assertEquals(LocalDate.of(2012, 5, 19), DataStore.parseDate("2012-05-19 18:30:00"));
        assertNull(DataStore.parseDate("NA"));
        assertNull(DataStore.parseDate("not a date"));
        assertNull(DataStore.parseDate("2023-13-45"));
    }

    @Test
    @DisplayName("Scenario: scores are parsed from integer, decimal and missing values")
    void scores() {
        assertEquals(2, DataStore.parseInt("2"));
        assertEquals(1, DataStore.parseInt("1.0"));
        assertNull(DataStore.parseInt("NA"));
        assertNull(DataStore.parseInt("-"));
        assertNull(DataStore.parseInt(""));
    }

    @Test
    @DisplayName("Scenario: UTF-8 accents survive loading")
    void utf8() {
        assertTrue(ds.players.stream().anyMatch(p -> p.club.equals("Grêmio")));
        assertEquals("São Paulo", ds.teams.display(ds.teams.canonical("Sao Paulo-SP")));
        assertEquals("Grêmio", ds.teams.display(ds.teams.canonical("Gremio")));
    }

    @Test
    @DisplayName("Scenario: overlapping files do not double count a season")
    void noDoubleCounting() {
        // Serie A 2015 appears in three files; exactly one is primary -> 380 matches
        long n = ds.matches.stream().filter(m -> m.primary && m.competition.equals(DataStore.SERIE_A) && m.season == 2015).count();
        assertEquals(380, n);
        long all = ds.matches.stream().filter(m -> m.competition.equals(DataStore.SERIE_A) && m.season == 2015).count();
        assertTrue(all > 380);
    }

    @Test
    @DisplayName("Scenario: CSV parser handles quotes, escaped quotes and embedded commas")
    void csvParser() {
        List<List<String>> rows = Csv.parse("a,b,c\r\n\"x, y\",\"he said \"\"hi\"\"\",3\n\"multi\nline\",,\n");
        assertEquals(3, rows.size());
        assertEquals(List.of("x, y", "he said \"hi\"", "3"), rows.get(1));
        assertEquals(List.of("multi\nline", "", ""), rows.get(2));
    }

    @Test
    @DisplayName("Scenario: a missing data directory is reported")
    void missingDirectory() {
        assertThrows(IOException.class, () -> DataStore.load(Path.of("no", "such", "dir")));
    }
}
