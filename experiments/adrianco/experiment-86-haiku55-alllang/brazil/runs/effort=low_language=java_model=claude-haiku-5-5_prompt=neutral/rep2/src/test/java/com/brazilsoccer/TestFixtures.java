package com.brazilsoccer;

import com.brazilsoccer.data.DataLoader;
import com.brazilsoccer.data.DataRepository;
import com.brazilsoccer.data.Match;
import com.brazilsoccer.data.Player;

import java.nio.file.Path;
import java.time.LocalDate;
import java.util.List;

/** Shared builders for small in-memory datasets and the real dataset location. */
public final class TestFixtures {

    public static final Path REAL_DATA_DIR = Path.of("data", "kaggle");

    private TestFixtures() {
    }

    public static Match match(String date, String competition, String home, int hg, String away, int ag) {
        return new Match(LocalDate.parse(date), competition, null, home, away, hg, ag);
    }

    /** A small Brasileirão 2023 slice plus one Copa do Brasil tie and one player per scenario. */
    public static DataRepository smallRepository() {
        List<Match> matches = List.of(
                match("2023-09-03", DataLoader.SERIE_A, "Flamengo-RJ", 2, "Fluminense-RJ", 1),
                match("2023-05-28", DataLoader.SERIE_A, "Fluminense-RJ", 1, "Flamengo-RJ", 0),
                match("2023-03-10", DataLoader.SERIE_A, "Palmeiras-SP", 3, "Santos-SP", 0),
                match("2023-04-02", DataLoader.SERIE_A, "Santos-SP", 1, "Palmeiras-SP", 1),
                match("2023-06-14", DataLoader.SERIE_A, "Palmeiras-SP", 2, "Corinthians-SP", 2),
                match("2023-07-19", DataLoader.COPA_DO_BRASIL, "Palmeiras", 4, "Flamengo", 1),
                match("2022-08-01", DataLoader.SERIE_A, "Corinthians-SP", 2, "Palmeiras-SP", 0));
        List<Player> players = List.of(
                new Player(1, "Neymar Jr", 31, "Brazil", 92, 92, "Paris Saint-Germain", "LW", 10),
                new Player(2, "Gabriel Barbosa", 26, "Brazil", 84, 86, "Flamengo", "ST", 9),
                new Player(3, "Diego Ribas", 35, "Brazil", 81, 81, "Flamengo", "CAM", 10),
                new Player(4, "Lionel Messi", 31, "Argentina", 94, 94, "FC Barcelona", "RF", 10));
        return new DataRepository(matches, players);
    }
}
