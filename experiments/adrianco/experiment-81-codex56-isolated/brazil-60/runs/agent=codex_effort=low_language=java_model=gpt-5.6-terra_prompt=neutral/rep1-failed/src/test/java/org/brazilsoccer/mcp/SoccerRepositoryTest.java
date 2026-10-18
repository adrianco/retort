package org.brazilsoccer.mcp;
import static org.junit.jupiter.api.Assertions.*;
import java.nio.file.Path;import org.junit.jupiter.api.*;

class SoccerRepositoryTest {
 static SoccerRepository repo; static SoccerService service;
 @BeforeAll static void load() throws Exception {repo=SoccerRepository.load(Path.of("data/kaggle"));service=new SoccerService(repo);}
 @Test void allSixProvidedFilesLoad() {assertTrue(repo.matches().size()>20000);assertTrue(repo.findPlayers(null,null,null,null,500).size()>0);}
 @Test void normalizesAccentsAndStateSuffixes() {assertTrue(Names.same("São Paulo-SP","Sao Paulo"));assertFalse(service.matches("Flamengo",null,null,null,null,null,20).isEmpty());}
 @Test void findsCrossDatasetMatchesWithScores() {Match m=service.matches("Flamengo","Sao Paulo",null,null,null,null,50).get(0);assertNotNull(m.competition());assertNotNull(m.home());assertTrue(m.homeGoals()>=0);}
 @Test void calculatesTeamRecord() {var record=service.teamStatistics("Palmeiras", "Brasileirão",2019,false);assertTrue((Integer)record.get("matches")>0);assertEquals((Integer)record.get("matches"),(Integer)record.get("wins")+(Integer)record.get("draws")+(Integer)record.get("losses"));}
 @Test void searchesPlayersByNationality() {var players=repo.findPlayers(null,"Brazil",null,null,100);assertFalse(players.isEmpty());}
 @Test void createsStandings() {assertFalse(service.standings("Brasileirão",2019).isEmpty());}
}
