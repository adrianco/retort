package com.braziliansoccer.mcp;

import java.util.*;
import java.util.stream.*;

public final class SoccerService {
    private final SoccerRepository repository;
    public SoccerService(SoccerRepository repository) { this.repository = repository; }
    public TeamStats teamStats(String team, Integer season, String competition, String venue) {
        int matches=0,wins=0,draws=0,losses=0,goalsFor=0,goalsAgainst=0;
        for (Match m : repository.findMatches(new MatchFilter(team, null, competition, season, null, null, null, Integer.MAX_VALUE))) {
            boolean home = Normalizer.matches(m.homeTeam(), team); if (venue != null && !venue.equalsIgnoreCase(home ? "home" : "away")) continue;
            int gf = home ? m.homeGoals() : m.awayGoals(), ga = home ? m.awayGoals() : m.homeGoals(); matches++; goalsFor += gf; goalsAgainst += ga;
            if (gf > ga) wins++; else if (gf == ga) draws++; else losses++;
        }
        return new TeamStats(team, matches, wins, draws, losses, goalsFor, goalsAgainst);
    }
    public TeamStats headToHead(String first, String second, Integer season, String competition) {
        List<Match> games = repository.findMatches(new MatchFilter(first, second, competition, season, null, null, null, Integer.MAX_VALUE)).stream().filter(m -> (Normalizer.matches(m.homeTeam(), first) && Normalizer.matches(m.awayTeam(), second)) || (Normalizer.matches(m.homeTeam(), second) && Normalizer.matches(m.awayTeam(), first))).toList();
        int w=0,d=0,l=0,gf=0,ga=0;
        for (Match m: games) { boolean home = Normalizer.matches(m.homeTeam(), first); int f=home?m.homeGoals():m.awayGoals(), a=home?m.awayGoals():m.homeGoals(); gf+=f;ga+=a; if(f>a)w++;else if(f==a)d++;else l++; }
        return new TeamStats(first, games.size(), w, d, l, gf, ga);
    }
    public List<TeamStats> standings(Integer season, String competition) {
        Map<String, TeamStats> table = new HashMap<>();
        for (Match m : repository.findMatches(new MatchFilter(null, null, competition, season, null, null, null, Integer.MAX_VALUE))) { update(table,m.homeTeam(),m.homeGoals(),m.awayGoals()); update(table,m.awayTeam(),m.awayGoals(),m.homeGoals()); }
        Comparator<TeamStats> order = Comparator.comparingInt(TeamStats::points).reversed()
                .thenComparing(Comparator.comparingInt((TeamStats t) -> t.goalsFor() - t.goalsAgainst()).reversed())
                .thenComparing(TeamStats::team);
        return table.values().stream().sorted(order).toList();
    }
    private static void update(Map<String,TeamStats> table,String team,int gf,int ga) { String key=Normalizer.key(team); TeamStats old=table.getOrDefault(key,new TeamStats(team,0,0,0,0,0,0)); table.put(key,new TeamStats(old.team(),old.matches()+1,old.wins()+(gf>ga?1:0),old.draws()+(gf==ga?1:0),old.losses()+(gf<ga?1:0),old.goalsFor()+gf,old.goalsAgainst()+ga)); }
    public Map<String,Object> aggregate(String competition, Integer season) {
        List<Match> games=repository.findMatches(new MatchFilter(null,null,competition,season,null,null,null,Integer.MAX_VALUE));
        int goals=games.stream().mapToInt(m->m.homeGoals()+m.awayGoals()).sum(); long homeWins=games.stream().filter(m->m.homeGoals()>m.awayGoals()).count();
        return Map.of("matches",games.size(),"goals",goals,"averageGoals",games.isEmpty()?0.0:(double)goals/games.size(),"homeWinRate",games.isEmpty()?0.0:homeWins*100.0/games.size());
    }
    public List<Match> biggestWins(String competition, Integer season, int limit) { return repository.findMatches(new MatchFilter(null,null,competition,season,null,null,null,Integer.MAX_VALUE)).stream().sorted(Comparator.comparingInt(Match::margin).reversed().thenComparing(Match::date,Comparator.nullsLast(Comparator.reverseOrder()))).limit(limit).toList(); }
}
