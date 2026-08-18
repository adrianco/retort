package com.braziliansoccer.mcp;

import java.time.LocalDate;

public record MatchFilter(String team, String opponent, String competition, Integer season, LocalDate from, LocalDate to,
                          String roundOrStage, int limit) {
    public static MatchFilter any() { return new MatchFilter(null, null, null, null, null, null, null, 100); }
}
