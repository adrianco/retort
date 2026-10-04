package br.soccer;

import java.time.LocalDate;
import java.util.LinkedHashSet;
import java.util.Set;

/** One played match, merged across source files when several describe the same fixture. */
public final class Match {
    public LocalDate date;
    public String competition;
    public int season;
    public String round;
    public String stage;
    public String homeKey;
    public String awayKey;
    public int homeGoals;
    public int awayGoals;
    public String stadium;
    public Integer homeCorners, awayCorners, homeShots, awayShots;
    public final Set<String> sources = new LinkedHashSet<>();

    public String home() {
        return TeamNames.display(homeKey);
    }

    public String away() {
        return TeamNames.display(awayKey);
    }

    public boolean involves(String key) {
        return homeKey.equals(key) || awayKey.equals(key);
    }

    public int margin() {
        return Math.abs(homeGoals - awayGoals);
    }

    /** "2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A 2023, Round 22)" */
    public String describe() {
        StringBuilder b = new StringBuilder();
        b.append(date).append(": ").append(home()).append(' ').append(homeGoals).append('-')
                .append(awayGoals).append(' ').append(away()).append(" (").append(competition)
                .append(' ').append(season);
        if (stage != null && !stage.isEmpty()) b.append(", ").append(stage);
        else if (round != null && !round.isEmpty()) b.append(", Round ").append(round);
        if (stadium != null && !stadium.isEmpty()) b.append(", ").append(stadium);
        b.append(')');
        return b.toString();
    }
}
