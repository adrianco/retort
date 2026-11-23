import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import com.fasterxml.jackson.databind.*;
import com.fasterxml.jackson.databind.node.*;
import java.nio.file.Path;
import java.time.Duration;
import java.util.*;

class SoccerTest {
    static SoccerServer server;
    static ObjectMapper json=SoccerServer.JSON;
    @BeforeAll static void givenTheSixDatasets() throws Exception {
        server=new SoccerServer(new SoccerData(Path.of("data/kaggle")));
    }
    static JsonNode ask(String name,Object... args) throws Exception {
        var a=json.createObjectNode();
        for(int i=0;i<args.length;i+=2) a.set((String)args[i],json.valueToTree(args[i+1]));
        var request=Map.of("jsonrpc","2.0","id",1,"method","tools/call","params",Map.of("name",name,"arguments",a));
        var result=server.handle(json.writeValueAsString(request)).path("result");
        assertFalse(result.path("isError").asBoolean(),result.toString());
        return json.readTree(result.at("/content/0/text").asText());
    }
    @ParameterizedTest @CsvSource({"Brasileirao_Matches,4180","Brazilian_Cup_Matches,1337","Libertadores_Matches,1255",
        "novo_campeonato_brasileiro,6886","BR-Football-Dataset,10296"})
    void whenSearchingOneSourceThenEveryRowIsReachable(String source,int count) throws Exception {
        var page=ask("matches","source",source,"offset",count-1);
        assertEquals(count,page.get("total").intValue());
        assertTrue(page.at("/rows/0/sources").has(source));
    }
    @Test void whenComparingDerbyRivalsThenBothVenuesAndScoresAreAvailable() throws Exception {
        var args=ask("matches","team","Flamengo-RJ","opponent","Fluminense","season",2019,"competition","Brasileirão","derby",true);
        assertEquals(2,args.get("total").intValue());
        var match=args.at("/rows/0");
        for(String key:List.of("homeGoals","awayGoals","date","competition")) assertTrue(match.hasNonNull(key));
        assertEquals(2,ask("records","team","Flamengo","opponent","Fluminense","season",2019,"competition","Serie A").at("/rows/0/matches").intValue());
    }
    @Test void whenRankingThe2019LeagueThenFlamengoHas90PointsFrom38Matches() throws Exception {
        var r=ask("records","season",2019,"competition","Serie A");
        assertEquals(20,r.get("total").intValue());
        assertEquals("Flamengo",r.at("/rows/0/label").asText());
        assertEquals(90,r.at("/rows/0/points").intValue());
        assertEquals(38,r.at("/rows/0/matches").intValue());
        assertEquals(28,r.at("/rows/0/wins").intValue());
    }
    @Test void whenFilteringHomeAndAwayThenRecordsPartitionTheSeason() throws Exception {
        for(String venue:List.of("home","away")) {
            var r=ask("records","season",2019,"competition","Serie A","team","Sport Club Corinthians Paulista","venue",venue).at("/rows/0");
            assertEquals(19,r.get("matches").intValue());
            assertEquals(19,r.get("wins").intValue()+r.get("losses").intValue()+r.get("draws").intValue());
        }
    }
    @Test void whenComparingSeasonsThenOnlyPlayedFixturesEnterAverages() throws Exception {
        var s=ask("summary","competition","Serie A","from","2018-01-01","to","2019-12-31","group","season");
        assertEquals(2,s.get("total").intValue());
        assertEquals(380,s.at("/rows/1/matches").intValue());
        assertEquals(876.0/380,s.at("/rows/1/goalsPerMatch").doubleValue(),0.0001);
    }
    @Test void whenFindingCupFinalsThenExcludeEarlierRounds() throws Exception {
        assertEquals(2,ask("matches","season",2012,"competition","Copa do Brasil","stage","final").get("total").intValue());
        assertEquals(2,ask("matches","season",2018,"competition","Libertadores","stage","final").get("total").intValue());
    }
    @Test void whenSearchingFifaThenReturnRatingsSkillsAndPagedResults() throws Exception {
        assertEquals(18207,ask("players","limit",1).get("total").intValue());
        var r=ask("players","nationality","Brazilian","name","neymar").at("/rows/0");
        assertEquals("Neymar Jr",r.get("Name").asText());
        assertEquals("92",r.get("Overall").asText());
        assertTrue(r.has("Dribbling"));
        assertEquals(0,ask("players","name","no such player").get("total").intValue());
    }
    @Test void whenJoiningClubDataThenReturnFifaRosterAndCompetitionRecords() throws Exception {
        var r=ask("club_profile","team","Gremio-RS","season",2019);
        assertTrue(r.at("/records/total").intValue()>=2);
        assertEquals("Grêmio",r.at("/players/rows/0/Club").asText());
    }
    @Test void whenAskingForBiggestWinsThenSortByAbsoluteScoreDifference() throws Exception {
        var rows=ask("matches","competition","Serie A","sort","margin","limit",10).get("rows");
        int previous=Integer.MAX_VALUE;
        for(var row:rows) {
            int margin=Math.abs(row.get("homeGoals").intValue()-row.get("awayGoals").intValue());
            assertTrue(margin<=previous && margin>=5);
            previous=margin;
        }
    }
    @Test void whenPagingStandingsThenReturnTheBottomFour() throws Exception {
        var page=ask("records","competition","Serie A","season",2020,"offset",16,"limit",4);
        var teams=new HashSet<String>();
        page.get("rows").forEach(r->teams.add(r.get("label").asText()));
        assertEquals(Set.of("Vasco da Gama","Goiás","Coritiba","Botafogo"),teams);
    }
    @Test void whenLookingUpExtendedFinalThenPreserveCornersAndSourceDate() throws Exception {
        var result=ask("matches","competition","Copa do Brasil","stage","final","season",2023);
        assertEquals(2,result.get("total").intValue());
        var last=result.at("/rows/0");
        assertEquals("2023-09-24",last.get("date").asText());
        assertEquals("6.0",last.at("/sources/BR-Football-Dataset/total_corners").asText());
    }
    @Test void whenComparingTeamsWithSimilarNamesThenKeepTheirMatchesSeparate() throws Exception {
        var r=ask("matches","team","Atlético Mineiro","competition","Serie A","season",2019);
        assertEquals(38,r.get("total").intValue());
        var rio=ask("matches","team","Flamengo - PI","competition","Copa do Brasil");
        assertTrue(rio.get("total").intValue()>0);
        for(var row:rio.get("rows"))
            assertTrue(row.get("home").asText().contains("PI")||row.get("away").asText().contains("PI"));
    }
    @Test void whenQueryingAnUndatedFixtureThenLeaveUnknownFieldsEmpty() throws Exception {
        var r=ask("matches","source","Libertadores_Matches","offset",1254);
        assertTrue(r.at("/rows/0/date").isNull());
        assertTrue(r.at("/rows/0/homeGoals").isNull());
    }
    @Test void whenLookingUpResultsThenQueriesMeetTimeBudgets() {
        assertTimeout(Duration.ofSeconds(2),()->ask("matches","team","São Paulo FC","limit",1));
        assertTimeout(Duration.ofSeconds(5),()->ask("records","sort","winRate","venue","away"));
    }
    @Test void whenClientInitializesThenCanDiscoverToolsAndRecoverFromBadInput() throws Exception {
        var init=server.handle("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-06-18\"}}");
        assertTrue(init.at("/result/capabilities").has("tools"));
        assertNull(server.handle("{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}"));
        assertEquals(5,server.handle("{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}").at("/result/tools").size());
        assertEquals(-32700,server.handle("{").at("/error/code").intValue());
        assertTrue(server.handle("{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":{\"name\":\"matches\",\"arguments\":{\"limit\":0}}}").at("/result/isError").booleanValue());
    }
}
