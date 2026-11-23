import java.util.*;
import java.time.LocalDate;
import java.util.stream.Stream;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

class SoccerQueries {
    final SoccerData data;
    SoccerQueries(SoccerData data) { this.data=data; }
    static final Map<String,String> descriptions=Map.of(
        "matches","Search fixtures, scores, schedules and tournament brackets. Newest first. Use sort=margin for biggest wins, derby=true for known rivalries. Source names are CSV basenames. Each match includes original source attributes.",
        "players","Search FIFA player attributes. Highest overall first. Name and club support partial matches. Use position=forward for the forward line.",
        "records","Calculate played matches, wins, draws, losses, goals, points and win rate. Team and opponent select a head-to-head. Group by team, season or competition. Venue selects the perspective. Sort by points (standings), goals or winRate.",
        "summary","Calculate goals per played match and home/away win rates over selected fixtures. Group by season or competition to compare trends.",
        "club_profile","Join a team's competition records to its highest-rated FIFA players. Season filters match data only.");
    static final String FILTERS="team opponent venue competition season from to stage round source derby";
    static final Map<String,String> fields=Map.of("matches",FILTERS+" sort","records",FILTERS+" group sort",
        "summary",FILTERS+" group","players","name club nationality position","club_profile","team season");
    static final Map<String,List<String>> choices=Map.of(
        "venue",List.of("home","away","either"),"source",SoccerData.FILES.subList(0,5));
    static List<Map<String,Object>> tools() {
        var result=new ArrayList<Map<String,Object>>();
        for(String name:new TreeSet<>(fields.keySet())) {
            var props=new LinkedHashMap<String,Object>();
            for(String f:(fields.get(name)+" limit offset").split(" ")) {
                String type=switch(f) {case "season","limit","offset"->"integer"; case "derby"->"boolean"; default->"string";};
                var spec=new HashMap<String,Object>(); spec.put("type",type);
                if(choices.containsKey(f)) spec.put("enum",choices.get(f));
                if(f.equals("group")) spec.put("enum",name.equals("summary")?List.of("season","competition"):List.of("team","season","competition"));
                if(f.equals("sort")) spec.put("enum",name.equals("matches")?List.of("date","margin"):List.of("points","goals","winRate"));
                if(f.equals("from")||f.equals("to")) spec.put("description","Inclusive ISO date YYYY-MM-DD");
                if(f.equals("limit")) {spec.put("minimum",1);spec.put("maximum",100);}
                if(f.equals("offset")) spec.put("minimum",0);
                props.put(f,spec);
            }
            result.add(Map.of("name",name,"description",descriptions.get(name),"inputSchema",Map.of(
                "type","object","properties",props,"additionalProperties",false,"required",name.equals("club_profile")?List.of("team"):List.of())));
        }
        return result;
    }
    static String val(JsonNode a,String k) { return a.path(k).asText(""); }
    Object query(String name,ObjectNode a) {
        var definition=tools().stream().filter(t->t.get("name").equals(name)).findFirst().orElseThrow(()->new IllegalArgumentException("Unknown tool "+name));
        Map<?,?> schema=(Map<?,?>)definition.get("inputSchema"), props=(Map<?,?>)schema.get("properties");
        a.fields().forEachRemaining(e->{
            String k=e.getKey(); JsonNode v=e.getValue();
            if(!(props.get(k) instanceof Map<?,?> p)) throw new IllegalArgumentException("Unknown argument "+k);
            boolean valid=switch((String)p.get("type")) {
                case "integer" -> v.isIntegralNumber() && v.canConvertToInt();
                case "boolean" -> v.isBoolean();
                default -> v.isTextual() && !v.asText().isBlank();
            };
            if(!valid || p.get("enum") instanceof List<?> options && !options.contains(v.asText()))
                throw new IllegalArgumentException("Invalid "+k);
        });
        int limit=a.path("limit").asInt(20), offset=a.path("offset").asInt(0);
        if(limit<1||limit>100||offset<0) throw new IllegalArgumentException("limit must be 1–100 and offset nonnegative");
        if(name.equals("players")) return page(players(a),a);
        if(name.equals("club_profile")) {
            if(!a.has("team")) throw new IllegalArgumentException("team is required");
            var p=a.deepCopy().put("club",val(a,"team"));
            return Map.of("team",val(a,"team"),"records",records(select(a),a.deepCopy().put("group","competition")),
                "players",page(players(p).stream().filter(player->data.team(player.get("Club")).equals(data.team(val(a,"team")))).toList(),a));
        }
        var selected=select(a);
        return switch(name) {
            case "matches" -> {
                Stream<SoccerData.Match> s=selected.stream();
                if(val(a,"sort").equals("margin")) s=s.filter(SoccerData.Match::played).sorted(Comparator.comparingInt(
                    (SoccerData.Match m)->Math.abs(m.homeGoals()-m.awayGoals())).reversed());
                yield page(s.toList(),a);
            }
            case "records" -> records(selected,a);
            default -> summary(selected,a);
        };
    }
    static Object page(List<?> list,JsonNode a) {
        int start=Math.min(list.size(),a.path("offset").asInt(0));
        int end=Math.min(list.size(),start+a.path("limit").asInt(20));
        return Map.of("total",list.size(),"offset",start,"rows",list.subList(start,end));
    }
    List<Map<String,String>> players(JsonNode a) {
        String name=SoccerData.fold(val(a,"name")), nation=SoccerData.fold(val(a,"nationality")),
            club=SoccerData.fold(data.team(val(a,"club"))), pos=val(a,"position").toUpperCase(Locale.ROOT);
        return data.players.stream().filter(p->SoccerData.fold(p.get("Name")).contains(name))
            .filter(p->nation.isEmpty()||SoccerData.fold(p.get("Nationality")).equals(nation.equals("brazilian")?"brazil":nation))
            .filter(p->club.isEmpty()||SoccerData.fold(data.team(p.get("Club"))).contains(club))
            .filter(p->pos.isEmpty()||p.get("Position").equals(pos)||pos.equals("FORWARD") &&
                Set.of("LS","ST","RS","LF","CF","RF","LW","RW").contains(p.get("Position"))).toList();
    }
    static final List<Set<String>> RIVALS=List.of(Set.of("Flamengo","Fluminense"),Set.of("Flamengo","Vasco da Gama"),
        Set.of("Grêmio","Internacional"),Set.of("Palmeiras","Corinthians"),Set.of("Atlético-MG","Cruzeiro"),
        Set.of("São Paulo","Corinthians"),Set.of("Palmeiras","São Paulo"),Set.of("Santos","Corinthians"),
        Set.of("São Paulo","Santos"),Set.of("Palmeiras","Santos"),Set.of("Botafogo","Flamengo"),
        Set.of("Botafogo","Fluminense"),Set.of("Botafogo","Vasco da Gama"),Set.of("Vasco da Gama","Fluminense"),Set.of("Bahia","Vitória"),Set.of("Fortaleza","Ceará"),Set.of("Athletico-PR","Coritiba"));
    boolean perspective(String self,String other,boolean home,JsonNode a) {
        String venue=val(a,"venue");
        return !(home?venue.equals("away"):venue.equals("home")) &&
            (!a.has("team")||self.equals(data.team(val(a,"team")))) &&
            (!a.has("opponent")||other.equals(data.team(val(a,"opponent"))));
    }
    List<SoccerData.Match> select(JsonNode a) {
        String source=val(a,"source"),comp=SoccerData.competition(val(a,"competition"));
        LocalDate from=a.has("from")?LocalDate.parse(val(a,"from")):LocalDate.MIN;
        LocalDate to=a.has("to")?LocalDate.parse(val(a,"to")):LocalDate.MAX;
        if(from.isAfter(to)) throw new IllegalArgumentException("from exceeds to");
        return (source.isEmpty()?data.matches:data.raw).stream()
            .filter(m->source.isEmpty()||m.sources().containsKey(source))
            .filter(m->comp.isEmpty()||m.competition().equalsIgnoreCase(comp))
            .filter(m->!a.has("season")||Objects.equals(a.get("season").asInt(),m.season()))
            .filter(m->m.date()==null ? !a.has("from")&&!a.has("to") : !m.date().isBefore(from)&&!m.date().isAfter(to))
            .filter(m->!a.has("round")||m.round().equals(val(a,"round")))
            .filter(m->!a.has("stage")||m.stage().equalsIgnoreCase(val(a,"stage")))
            .filter(m->!a.path("derby").asBoolean()||RIVALS.stream().anyMatch(r->r.contains(m.home())&&r.contains(m.away())&&!m.home().equals(m.away())))
            .filter(m->perspective(m.home(),m.away(),true,a)||perspective(m.away(),m.home(),false,a)).toList();
    }
    static class Record {
        public final String label;
        public int matches,wins,draws,losses,goalsFor,goalsAgainst,points;
        Record(String label) {this.label=label;}
        void add(int scored,int conceded) {
            matches++; goalsFor+=scored; goalsAgainst+=conceded;
            if(scored>conceded) { wins++; points+=3; }
            else if(scored==conceded) { draws++; points++; }
            else losses++;
        }
        public double getWinRate() {return wins*100.0/matches;}
        public int getGoalDifference() {return goalsFor-goalsAgainst;}
    }
    Object records(List<SoccerData.Match> selected,JsonNode a) {
        var groups=new TreeMap<String,Record>();
        for(var m:selected) if(m.played()) {
            for(boolean home:List.of(true,false)) {
                String team=home?m.home():m.away();
                if(!perspective(team,home?m.away():m.home(),home,a)) continue;
                String key=switch(val(a,"group")) {
                    case "competition"->m.competition(); case "season"->""+m.season(); default->team;
                };
                groups.computeIfAbsent(key,Record::new).add(home?m.homeGoals():m.awayGoals(),home?m.awayGoals():m.homeGoals());
            }
        }
        Comparator<Record> rank=Comparator.comparingInt((Record r)->r.points).thenComparingInt(r->r.wins)
            .thenComparingInt(Record::getGoalDifference).thenComparingInt(r->r.goalsFor);
        if(val(a,"sort").equals("goals")) rank=Comparator.comparingInt((Record r)->r.goalsFor).thenComparing(rank);
        if(val(a,"sort").equals("winRate")) rank=Comparator.comparingDouble(Record::getWinRate).thenComparing(rank);
        return page(groups.values().stream().sorted(rank.reversed()).toList(),a);
    }
    Object summary(List<SoccerData.Match> selected,JsonNode a) {
        var groups=new TreeMap<String,Record>();
        for(var m:selected) if(m.played()) {
            String key=switch(val(a,"group")) {case "season"->""+m.season(); case "competition"->m.competition(); default->"all";};
            groups.computeIfAbsent(key,Record::new).add(m.homeGoals(),m.awayGoals());
        }
        return page(groups.values().stream().map(r->Map.of("label",r.label,"matches",r.matches,"goalsPerMatch",
            (r.goalsFor+r.goalsAgainst)/(double)r.matches,"homeWinRate",r.getWinRate(),"awayWinRate",100.0*r.losses/r.matches,"draws",r.draws)).toList(),a);
    }
}
