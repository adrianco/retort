package com.brsoccer.mcp.model;

public class Player {
    private final String id;
    private final String name;
    private final Integer age;
    private final String nationality;
    private final Integer overall;
    private final Integer potential;
    private final String club;
    private final String clubNormalized;
    private final String position;
    private final String jerseyNumber;
    private final String height;
    private final String weight;
    private final String preferredFoot;

    private Player(Builder b) {
        this.id = b.id;
        this.name = b.name;
        this.age = b.age;
        this.nationality = b.nationality;
        this.overall = b.overall;
        this.potential = b.potential;
        this.club = b.club;
        this.clubNormalized = b.clubNormalized;
        this.position = b.position;
        this.jerseyNumber = b.jerseyNumber;
        this.height = b.height;
        this.weight = b.weight;
        this.preferredFoot = b.preferredFoot;
    }

    public String getId() { return id; }
    public String getName() { return name; }
    public Integer getAge() { return age; }
    public String getNationality() { return nationality; }
    public Integer getOverall() { return overall; }
    public Integer getPotential() { return potential; }
    public String getClub() { return club; }
    public String getClubNormalized() { return clubNormalized; }
    public String getPosition() { return position; }
    public String getJerseyNumber() { return jerseyNumber; }
    public String getHeight() { return height; }
    public String getWeight() { return weight; }
    public String getPreferredFoot() { return preferredFoot; }

    public static Builder builder() { return new Builder(); }

    public static class Builder {
        private String id;
        private String name;
        private Integer age;
        private String nationality;
        private Integer overall;
        private Integer potential;
        private String club;
        private String clubNormalized;
        private String position;
        private String jerseyNumber;
        private String height;
        private String weight;
        private String preferredFoot;

        public Builder id(String v) { this.id = v; return this; }
        public Builder name(String v) { this.name = v; return this; }
        public Builder age(Integer v) { this.age = v; return this; }
        public Builder nationality(String v) { this.nationality = v; return this; }
        public Builder overall(Integer v) { this.overall = v; return this; }
        public Builder potential(Integer v) { this.potential = v; return this; }
        public Builder club(String v) { this.club = v; return this; }
        public Builder clubNormalized(String v) { this.clubNormalized = v; return this; }
        public Builder position(String v) { this.position = v; return this; }
        public Builder jerseyNumber(String v) { this.jerseyNumber = v; return this; }
        public Builder height(String v) { this.height = v; return this; }
        public Builder weight(String v) { this.weight = v; return this; }
        public Builder preferredFoot(String v) { this.preferredFoot = v; return this; }

        public Player build() { return new Player(this); }
    }
}
