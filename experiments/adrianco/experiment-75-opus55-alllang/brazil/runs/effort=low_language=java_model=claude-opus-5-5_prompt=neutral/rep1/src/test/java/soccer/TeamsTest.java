package soccer;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class TeamsTest {
    @Test void stateSuffixesAndAccentsNormalize() {
        assertEquals(Teams.key("Palmeiras-SP"), Teams.key("Palmeiras"));
        assertEquals(Teams.key("São Paulo"), Teams.key("Sao Paulo-SP"));
        assertEquals(Teams.key("Grêmio"), Teams.key("Gremio - RS"));
        assertEquals("corinthians", Teams.key("Sport Club Corinthians Paulista"));
        assertEquals(Teams.key("Athletico-PR"), Teams.key("Atletico Paranaense"));
        assertEquals(Teams.key("Atlético - MG"), Teams.key("Atletico Mineiro"));
        assertNotEquals(Teams.key("Atletico-MG"), Teams.key("Atletico-GO"));
        assertEquals("nacional", Teams.key("Nacional (URU)"));
    }

    @Test void queryMatchesVariants() {
        assertTrue(Teams.matches("Flamengo-RJ", "flamengo"));
        assertTrue(Teams.matches("América - MG", "America MG"));
        assertFalse(Teams.matches("Fluminense-RJ", "Flamengo"));
    }

    @Test void csvHandlesQuotesAndCommas() {
        var rows = Csv.parse("a,b\n\"x, y\",\"he said \"\"hi\"\"\"\n");
        assertEquals("x, y", rows.get(1).get(0));
        assertEquals("he said \"hi\"", rows.get(1).get(1));
    }

    @Test void multipleDateFormats() {
        assertEquals("2003-03-29", DataStore.date("29/03/2003").toString());
        assertEquals("2012-05-19", DataStore.date("2012-05-19 18:30:00").toString());
        assertEquals("2023-09-24", DataStore.date("2023-09-24").toString());
    }
}
