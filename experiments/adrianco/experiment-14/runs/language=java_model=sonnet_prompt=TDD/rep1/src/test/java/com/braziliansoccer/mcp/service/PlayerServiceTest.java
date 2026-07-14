package com.braziliansoccer.mcp.service;

import com.braziliansoccer.mcp.model.Player;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;

class PlayerServiceTest {
    private PlayerService service;

    @BeforeEach void setUp() {
        List<Player> testPlayers = List.of(
            new Player("1", "Lionel Messi", 32, "Argentina", "FC Barcelona", "RW", 94, 94),
            new Player("2", "Cristiano Ronaldo", 34, "Portugal", "Juventus", "ST", 93, 93),
            new Player("3", "Neymar Jr", 27, "Brazil", "Paris Saint-Germain", "LW", 92, 92),
            new Player("4", "Alisson", 26, "Brazil", "Liverpool", "GK", 89, 91),
            new Player("5", "Firmino", 27, "Brazil", "Liverpool", "ST", 87, 87)
        );
        service = new PlayerService(testPlayers);
    }

    @Test void testFindByName() {
        List<Player> r = service.findByName("messi");
        assertEquals(1, r.size());
        assertEquals("Lionel Messi", r.get(0).name());
    }
    @Test void testFindByNationality() { assertEquals(3, service.findByNationality("Brazil").size()); }
    @Test void testFindByClub() { assertEquals(2, service.findByClub("liverpool").size()); }
    @Test void testGetTopPlayers() {
        List<Player> r = service.getTopPlayers(3);
        assertEquals(3, r.size());
        assertEquals("Lionel Messi", r.get(0).name());
        assertEquals("Cristiano Ronaldo", r.get(1).name());
    }
    @Test void testGetTopPlayersByClub() {
        List<Player> r = service.getTopPlayersByClub("Liverpool", 5);
        assertEquals(2, r.size());
        assertEquals("Alisson", r.get(0).name());
    }
}
