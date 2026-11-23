import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.*;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.*;
import com.fasterxml.jackson.databind.node.*;

public class SoccerServer {
    static final ObjectMapper JSON=new ObjectMapper().findAndRegisterModules().disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
    final SoccerQueries queries;
    SoccerServer(SoccerData data) { queries=new SoccerQueries(data); }
    static ObjectNode envelope(JsonNode id) {
        return JSON.createObjectNode().put("jsonrpc","2.0").set("id",id);
    }
    static ObjectNode error(JsonNode id,int code,String message) {
        return envelope(id).set("error",JSON.valueToTree(Map.of("code",code,"message",message)));
    }
    ObjectNode handle(String line) throws JsonProcessingException {
        JsonNode req;
        try {req=JSON.readTree(line);} catch(JsonProcessingException e) {return error(null,-32700,"Invalid JSON");}
        if(req==null || !req.isObject() || !req.path("jsonrpc").asText().equals("2.0") || !req.path("method").isTextual())
            return error(null,-32600,"Invalid JSON-RPC request");
        var id=req.get("id");
        if(id==null) return null;
        JsonNode params=req.path("params");
        Object result;
        switch(req.get("method").asText()) {
            case "initialize" -> {
                String version=params.path("protocolVersion").asText();
                if(!Set.of("2024-11-05","2025-03-26","2025-06-18").contains(version)) version="2025-06-18";
                result=Map.of("protocolVersion",version,"capabilities",Map.of("tools",Map.of()),
                    "serverInfo",Map.of("name","brazilian-soccer","version","1.0"),
                    "instructions","Answer questions using the selected dataset and season. Results can be partial. Rank league teams by computed points. Goal scorer identities and administrative decisions are unavailable. Use offset to continue a page.");
            }
            case "ping" -> result=Map.of();
            case "tools/list" -> result=Map.of("tools",SoccerQueries.tools());
            case "tools/call" -> {
                String tool=params.path("name").asText();
                if(!SoccerQueries.fields.containsKey(tool)) return error(id,-32602,"Unknown tool");
                JsonNode args=params.path("arguments");
                if(args.isMissingNode()) args=JSON.createObjectNode();
                if(!(args instanceof ObjectNode object)) return error(id,-32602,"Expected arguments object");
                try {
                    result=content(JSON.writeValueAsString(queries.query(tool,object)),false);
                } catch(IllegalArgumentException | java.time.DateTimeException e) { result=content(e.getMessage(),true); }
            }
            default -> {return error(id,-32601,"Unknown method");}
        }
        return envelope(id).set("result",JSON.valueToTree(result));
    }
    static Object content(String text,boolean failed) {
        return Map.of("content",List.of(Map.of("type","text","text",text)),"isError",failed);
    }
    public static void main(String[] args) throws IOException {
        var server=new SoccerServer(new SoccerData(Path.of(args.length>0?args[0]:"data/kaggle")));
        var reader=new BufferedReader(new InputStreamReader(System.in,StandardCharsets.UTF_8));
        var out=new PrintWriter(System.out,true,StandardCharsets.UTF_8);
        for(String line;(line=reader.readLine())!=null;) {
            ObjectNode reply=server.handle(line);
            if(reply!=null) out.println(JSON.writeValueAsString(reply));
        }
    }
}
