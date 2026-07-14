package com.example.soccer;

import com.example.soccer.data.CsvLoader;
import com.example.soccer.model.Match;
import com.example.soccer.model.Player;
import org.junit.jupiter.api.Test;

import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

public class CsvLoaderTest {
    private static final Path DATA = CsvLoader.defaultDataDir();

    @Test void loadsBrasileiraoMatches() throws Exception {
        List<Match> ms = new CsvLoader().loadBrasileirao(DATA.resolve("Brasileirao_Matches.csv"));
        assertTrue(ms.size() > 4000, "expected >4000, got " + ms.size());
        assertTrue(ms.stream().allMatch(m -> m.homeTeam != null && m.awayTeam != null));
    }

    @Test void loadsFifaPlayers() throws Exception {
        List<Player> ps = new CsvLoader().loadFifaPlayers(DATA.resolve("fifa_data.csv"));
        assertTrue(ps.size() > 18000, "expected >18000, got " + ps.size());
        assertTrue(ps.stream().anyMatch(p -> "Brazil".equalsIgnoreCase(p.nationality)));
    }

    @Test void loadAllReturnsAllDatasets() throws Exception {
        CsvLoader.Dataset ds = new CsvLoader().loadAll(DATA);
        assertTrue(ds.matches.size() > 20000, "matches: " + ds.matches.size());
        assertTrue(ds.players.size() > 18000, "players: " + ds.players.size());
    }
}
