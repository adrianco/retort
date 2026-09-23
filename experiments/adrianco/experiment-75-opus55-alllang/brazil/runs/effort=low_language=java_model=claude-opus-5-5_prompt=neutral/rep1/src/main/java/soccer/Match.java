package soccer;

import java.time.LocalDate;

public record Match(LocalDate date, String home, String away, int homeGoals, int awayGoals,
                    String competition, int season, String round, String source, String arena) {
    public String homeKey() { return Teams.key(home); }
    public String awayKey() { return Teams.key(away); }
    public int totalGoals() { return homeGoals + awayGoals; }
    public boolean involves(String team) { return Teams.matches(home, team) || Teams.matches(away, team); }

    public String format() {
        String r = round == null || round.isBlank() ? "" : (competition.startsWith("Brasileir") ? " Round " : " ") + round;
        return String.format("%s: %s %d-%d %s (%s %d%s)", date, Teams.display(home), homeGoals, awayGoals,
                Teams.display(away), competition, season, r);
    }
}
