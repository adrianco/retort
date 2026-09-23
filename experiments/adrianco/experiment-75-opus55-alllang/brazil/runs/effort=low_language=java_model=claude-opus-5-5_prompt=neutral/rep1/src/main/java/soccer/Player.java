package soccer;

public record Player(int id, String name, int age, String nationality, int overall, int potential,
                     String club, String position, String jersey, String height, String weight, String value) {
    public String format() {
        return String.format("%s - Overall: %d, Potential: %d, Position: %s, Age: %d, Nationality: %s, Club: %s",
                name, overall, potential, position, age, nationality, club.isEmpty() ? "(none)" : club);
    }
}
