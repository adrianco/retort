package com.example.brsoccer.model;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;

class MatchTest {

    private Match match(String home, int hg, int ag, String away) {
        return new Match("Brasileirão", 2023, LocalDate.of(2023, 9, 3), "22",
                home, away, hg, ag);
    }

    @Test
    void detectsHomeWin() {
        Match m = match("Flamengo", 2, 1, "Fluminense");
        assertTrue(m.isHomeWin());
        assertFalse(m.isAwayWin());
        assertFalse(m.isDraw());
        assertEquals(Optional.of("Flamengo"), m.winner());
    }

    @Test
    void detectsAwayWin() {
        Match m = match("Flamengo", 0, 2, "Fluminense");
        assertTrue(m.isAwayWin());
        assertEquals(Optional.of("Fluminense"), m.winner());
    }

    @Test
    void detectsDraw() {
        Match m = match("Flamengo", 1, 1, "Fluminense");
        assertTrue(m.isDraw());
        assertEquals(Optional.empty(), m.winner());
    }

    @Test
    void totalGoalsSumsBothSides() {
        assertEquals(4, match("A", 3, 1, "B").totalGoals());
    }

    @Test
    void involvesMatchesEitherSideIgnoringSuffix() {
        Match m = match("Palmeiras-SP", 2, 0, "Santos-SP");
        assertTrue(m.involves("palmeiras"));
        assertTrue(m.involves("Santos"));
        assertFalse(m.involves("Corinthians"));
    }

    @Test
    void isBetweenMatchesBothTeamsRegardlessOfOrder() {
        Match m = match("Palmeiras-SP", 2, 0, "Santos");
        assertTrue(m.isBetween("santos", "palmeiras"));
        assertTrue(m.isBetween("Palmeiras", "Santos"));
        assertFalse(m.isBetween("Palmeiras", "Corinthians"));
    }

    @Test
    void goalDifferenceIsHomeMinusAway() {
        assertEquals(2, match("A", 3, 1, "B").goalDifference());
        assertEquals(3, match("A", 1, 4, "B").goalMargin());
    }
}
