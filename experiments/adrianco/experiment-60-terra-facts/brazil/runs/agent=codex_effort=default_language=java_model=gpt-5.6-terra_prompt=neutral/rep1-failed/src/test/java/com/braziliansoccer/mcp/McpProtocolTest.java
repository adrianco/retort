package com.braziliansoccer.mcp;

import org.junit.jupiter.api.Test;
import java.nio.file.*;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;

class McpProtocolTest {
    @Test void advertisesAndCallsToolsOverJsonRpc() throws Exception { Path dir=Files.createTempDirectory("mcp"); String empty="datetime,home_team,home_team_state,away_team,away_team_state,home_goal,away_goal,season,round\n"; Files.writeString(dir.resolve("Brasileirao_Matches.csv"),empty);Files.writeString(dir.resolve("Brazilian_Cup_Matches.csv"),"round,datetime,home_team,away_team,home_goal,away_goal,season\n");Files.writeString(dir.resolve("Libertadores_Matches.csv"),"datetime,home_team,away_team,home_goal,away_goal,season,stage\n");Files.writeString(dir.resolve("BR-Football-Dataset.csv"),"tournament,home,home_goal,away_goal,away,time,date\n");Files.writeString(dir.resolve("novo_campeonato_brasileiro.csv"),"ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante\n");Files.writeString(dir.resolve("fifa_data.csv"),"ID,Name,Age,Nationality,Overall,Potential,Club,Position\n1,Gabriel Barbosa,26,Brazil,82,84,Flamengo,ST\n");
        BrazilianSoccerMcpServer server=new BrazilianSoccerMcpServer(SoccerRepository.load(dir)); Map<String,Object> listed=Json.object(server.handle(Map.of("jsonrpc","2.0","id",1,"method","tools/list")));Map<String,Object> result=Json.object(listed.get("result"));assertEquals(7,((List<?>)result.get("tools")).size());Map<String,Object> call=Json.object(server.handle(Map.of("jsonrpc","2.0","id",2,"method","tools/call","params",Map.of("name","search_players","arguments",Map.of("name","Gabriel")))));assertTrue(Json.stringify(call).contains("Gabriel Barbosa")); }
}
