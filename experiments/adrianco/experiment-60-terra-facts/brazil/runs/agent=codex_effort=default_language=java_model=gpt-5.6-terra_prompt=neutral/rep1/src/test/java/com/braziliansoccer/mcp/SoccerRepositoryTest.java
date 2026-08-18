package com.braziliansoccer.mcp;

import org.junit.jupiter.api.*;
import java.nio.file.*;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;

class SoccerRepositoryTest {
    private SoccerRepository repository;
    @BeforeEach void loadFixture() throws Exception { Path dir=Files.createTempDirectory("soccer-fixture");
        write(dir,"Brasileirao_Matches.csv","datetime,home_team,home_team_state,away_team,away_team_state,home_goal,away_goal,season,round\n2023-09-03 16:00:00,Flamengo-RJ,RJ,Fluminense-RJ,RJ,2,1,2023,22\n2023-05-28 16:00:00,Fluminense-RJ,RJ,Flamengo-RJ,RJ,1,0,2023,8\n");
        write(dir,"Brazilian_Cup_Matches.csv","round,datetime,home_team,away_team,home_goal,away_goal,season\nFinal,2023-09-24,Flamengo,Sao Paulo,1,1,2023\n");
        write(dir,"Libertadores_Matches.csv","datetime,home_team,away_team,home_goal,away_goal,season,stage\n2023-08-01,Palmeiras,Atletico-MG,2,0,2023,knockout\n");
        write(dir,"BR-Football-Dataset.csv","tournament,home,home_goal,away_goal,away,time,date\nCopa do Brasil,Flamengo,0,1,Sao Paulo,20:00,2023-09-17\n");
        write(dir,"novo_campeonato_brasileiro.csv","ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena\n1,29/03/2003,2003,1,Guarani,Vasco,4,2,SP,RJ,Mandante,Brinco\n");
        write(dir,"fifa_data.csv","ID,Name,Age,Nationality,Overall,Potential,Club,Position\n1,Gabriel Barbosa,26,Brazil,82,84,Flamengo,ST\n2,Neymar Jr,31,Brazil,91,91,PSG,LW\n"); repository=SoccerRepository.load(dir); }
    @Test void supportsNormalizedCrossFileTeamSearch() { List<Match> matches=repository.findMatches(new MatchFilter("Flamengo",null,null,2023,null,null,null,20)); assertEquals(4,matches.size()); assertTrue(matches.stream().allMatch(m->m.homeTeam().contains("Flamengo")||m.awayTeam().contains("Flamengo"))); }
    @Test void parsesBrazilianDatesAndLoadsEveryCsv() { assertEquals(6,repository.matches().size()); assertTrue(repository.matches().stream().anyMatch(m->m.date().toString().equals("2003-03-29"))); }
    @Test void findsPlayersWithoutAccentOrCaseSensitivity() { List<Player> players=repository.findPlayers("gabriel", "brazil", "flamengo", null,10);assertEquals("Gabriel Barbosa",players.getFirst().name()); }
    @Test void calculatesRecordsHeadToHeadAndStandings() { SoccerService soccer=new SoccerService(repository); TeamStats record=soccer.teamStats("Flamengo",2023,"Brasileirão",null);assertEquals(2,record.matches());assertEquals(1,record.wins());assertEquals(1,record.losses());TeamStats h2h=soccer.headToHead("Flamengo","Fluminense",2023,"Brasileirão");assertEquals(2,h2h.matches());assertEquals(1,h2h.wins());assertEquals(1,h2h.losses());assertEquals("Flamengo-RJ",soccer.standings(2023,"Brasileirão").getFirst().team()); }
    @Test void aggregatesAndRanksBiggestWin() { SoccerService soccer=new SoccerService(repository);assertEquals(2.0,soccer.aggregate("Brasileirão",2023).get("averageGoals"));assertEquals(1,soccer.biggestWins("Brasileirão",2023,1).getFirst().margin()); }
    @Test void keepsAtleticoMineiroSeparateFromAthleticoParanaenseInStandings() throws Exception {
        Path dir = Files.createTempDirectory("atletico-identity");
        write(dir,"Brasileirao_Matches.csv","datetime,home_team,home_team_state,away_team,away_team_state,home_goal,away_goal,season,round\n"
                + "2023-01-01,Atletico-MG,MG,Flamengo-RJ,RJ,1,0,2023,1\n"
                + "2023-01-02,Athletico Paranaense,PR,Flamengo-RJ,RJ,2,0,2023,1\n"
                + "2023-01-03,Atletico Paranaense,PR,Atletico-MG,MG,1,1,2023,2\n");
        write(dir,"Brazilian_Cup_Matches.csv","round,datetime,home_team,away_team,home_goal,away_goal,season\n");
        write(dir,"Libertadores_Matches.csv","datetime,home_team,home_goal,away_team,away_goal,season,stage\n");
        write(dir,"BR-Football-Dataset.csv","tournament,home,home_goal,away_goal,away,time,date\n");
        write(dir,"novo_campeonato_brasileiro.csv","ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante\n");
        write(dir,"fifa_data.csv","ID,Name,Age,Nationality,Overall,Potential,Club,Position\n");
        List<TeamStats> table = new SoccerService(SoccerRepository.load(dir)).standings(2023,"Brasileirão");
        assertEquals(3,table.size());
        assertEquals(2,table.stream().filter(t -> t.team().contains("Paranaense") || t.team().contains("Athletico")).findFirst().orElseThrow().matches());
        assertEquals(2,table.stream().filter(t -> t.team().contains("MG")).findFirst().orElseThrow().matches());
    }
    @Test void producesTheCompleteTwentyClub2019SerieATableFromTheSuppliedData() throws Exception {
        List<TeamStats> table = new SoccerService(SoccerRepository.load(Path.of("data/kaggle"))).standings(2019,"Brasileirão");
        assertEquals(20, table.size(), table.toString());
        assertEquals(38, table.stream().filter(t -> t.team().equals("Atletico-MG")).findFirst().orElseThrow().matches());
        assertEquals(38, table.stream().filter(t -> t.team().equals("Atletico-PR")).findFirst().orElseThrow().matches());
        assertEquals(38, table.stream().filter(t -> t.team().startsWith("Vasco")).findFirst().orElseThrow().matches());
    }
    private static void write(Path dir,String name,String data) throws Exception {Files.writeString(dir.resolve(name),data);}
}
