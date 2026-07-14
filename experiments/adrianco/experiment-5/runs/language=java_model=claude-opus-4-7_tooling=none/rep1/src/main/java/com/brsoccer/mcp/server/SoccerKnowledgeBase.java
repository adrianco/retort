package com.brsoccer.mcp.server;

import com.brsoccer.mcp.data.DataLoader;
import com.brsoccer.mcp.model.Competition;
import com.brsoccer.mcp.model.Match;
import com.brsoccer.mcp.model.Player;
import com.brsoccer.mcp.service.CompetitionService;
import com.brsoccer.mcp.service.MatchService;
import com.brsoccer.mcp.service.PlayerService;
import com.brsoccer.mcp.service.StatsService;
import com.brsoccer.mcp.service.TeamService;

import java.io.IOException;
import java.nio.file.Path;
import java.util.List;

/**
 * Composite facade aggregating all services and providing easy access for the MCP server.
 */
public class SoccerKnowledgeBase {

    private final MatchService matchService;
    private final TeamService teamService;
    private final PlayerService playerService;
    private final CompetitionService competitionService;
    private final StatsService statsService;

    public SoccerKnowledgeBase(Path dataDir) throws IOException {
        DataLoader loader = new DataLoader(dataDir);
        loader.loadAll();
        this.matchService = new MatchService(loader.getMatches());
        this.teamService = new TeamService(matchService);
        this.playerService = new PlayerService(loader.getPlayers());
        this.competitionService = new CompetitionService(matchService);
        this.statsService = new StatsService(matchService);
    }

    public SoccerKnowledgeBase(List<Match> matches, List<Player> players) {
        this.matchService = new MatchService(matches);
        this.teamService = new TeamService(matchService);
        this.playerService = new PlayerService(players);
        this.competitionService = new CompetitionService(matchService);
        this.statsService = new StatsService(matchService);
    }

    public MatchService matches() { return matchService; }
    public TeamService teams() { return teamService; }
    public PlayerService players() { return playerService; }
    public CompetitionService competitions() { return competitionService; }
    public StatsService stats() { return statsService; }

    public static Competition parseCompetition(String s) {
        if (s == null) return null;
        switch (s.trim().toLowerCase()) {
            case "brasileirao":
            case "brasileirão":
            case "serie_a":
            case "serie a":
                return Competition.BRASILEIRAO;
            case "copa_do_brasil":
            case "copa do brasil":
            case "cup":
                return Competition.COPA_DO_BRASIL;
            case "libertadores":
            case "copa libertadores":
                return Competition.LIBERTADORES;
            case "historical":
            case "historical_brasileirao":
                return Competition.HISTORICAL_BRASILEIRAO;
            case "extended":
                return Competition.EXTENDED;
            default:
                return Competition.fromString(s);
        }
    }
}
