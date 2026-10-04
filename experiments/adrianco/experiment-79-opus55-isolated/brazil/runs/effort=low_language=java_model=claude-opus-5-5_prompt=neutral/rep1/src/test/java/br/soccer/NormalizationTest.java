package br.soccer;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

@DisplayName("Feature: Data quality handling")
class NormalizationTest {

    @Test
    @DisplayName("Scenario: team name variations from different files map to one club")
    void teamNameVariations() {
        for (String v : List.of("Palmeiras-SP", "Palmeiras", "Palmeiras - SP", "SE Palmeiras", "palmeiras")) {
            assertEquals("palmeiras", TeamNames.canonical(v), v);
        }
        for (String v : List.of("São Paulo", "Sao Paulo-SP", "São Paulo - SP", "Sao Paulo", "São Paulo FC")) {
            assertEquals("sao paulo", TeamNames.canonical(v), v);
        }
        for (String v : List.of("Atlético-MG", "Atletico-MG", "Atletico Mineiro", "Atlético - MG")) {
            assertEquals("atletico mineiro", TeamNames.canonical(v), v);
        }
        for (String v : List.of("Athletico-PR", "Atletico-PR", "Atlético Paranaense - PR", "Athletico")) {
            assertEquals("athletico paranaense", TeamNames.canonical(v), v);
        }
        assertEquals("corinthians", TeamNames.canonical("Sport Club Corinthians Paulista"));
        assertEquals("vasco", TeamNames.canonical("Vasco da Gama-RJ"));
        assertEquals("gremio", TeamNames.canonical("Grêmio"));
        assertEquals("boavista",
                TeamNames.canonical("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"));
        assertEquals("asa", TeamNames.canonical("A.s.a. - AL"));
    }

    @Test
    @DisplayName("Scenario: namesake clubs from different states stay distinct")
    void namesakesStayDistinct() {
        assertNotEquals(TeamNames.canonical("Atletico-MG"), TeamNames.canonical("Atletico-GO"));
        assertNotEquals(TeamNames.canonical("Botafogo-RJ"), TeamNames.canonical("Botafogo SP"));
        assertNotEquals(TeamNames.canonical("América-MG"), TeamNames.canonical("América-RN"));
    }

    @Test
    @DisplayName("Scenario: canonical keys are displayed with Portuguese accents")
    void displayNames() {
        assertEquals("São Paulo", TeamNames.display("sao paulo"));
        assertEquals("Grêmio", TeamNames.display(TeamNames.canonical("Gremio-RS")));
        assertEquals("Flamengo", TeamNames.display(TeamNames.canonical("Flamengo-RJ")));
    }

    @Test
    @DisplayName("Scenario: ISO, ISO-with-time and Brazilian date formats are parsed")
    void dateFormats() {
        assertEquals(LocalDate.of(2023, 9, 24), DataStore.parseDate("2023-09-24"));
        assertEquals(LocalDate.of(2003, 3, 29), DataStore.parseDate("29/03/2003"));
        assertEquals(LocalDate.of(2012, 5, 19), DataStore.parseDate("2012-05-19 18:30:00"));
        assertNull(DataStore.parseDate("not a date"));
        assertNull(DataStore.parseDate("2023-13-45"));
    }

    @Test
    @DisplayName("Scenario: CSV parsing handles quotes, embedded commas and escaped quotes")
    void csvParsing() {
        List<List<String>> rows = Csv.parse("a,\"b,c\",\"d \"\"e\"\"\"\r\n1,,3\n");
        assertEquals(List.of(List.of("a", "b,c", "d \"e\""), List.of("1", "", "3")), rows);
    }

    @Test
    @DisplayName("Scenario: JSON round-trips including UTF-8 and escapes")
    void json() {
        Object v = Json.parse("{\"a\":[1,2.5,true,null],\"b\":\"S\\u00e3o \\\"Paulo\\\"\\n\"}");
        Map<?, ?> m = (Map<?, ?>) v;
        assertEquals("São \"Paulo\"\n", m.get("b"));
        assertEquals(v, Json.parse(Json.write(v)));
        assertThrows(IllegalArgumentException.class, () -> Json.parse("{\"a\":"));
        assertThrows(IllegalArgumentException.class, () -> Json.parse("{} x"));
    }
}
