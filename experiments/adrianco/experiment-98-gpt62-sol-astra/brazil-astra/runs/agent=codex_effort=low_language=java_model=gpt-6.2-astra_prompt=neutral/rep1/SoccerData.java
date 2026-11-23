import java.io.*;
import java.nio.file.*;
import java.text.Normalizer;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.function.Consumer;
import org.apache.commons.csv.*;

class SoccerData {
    static final String LEAGUE = "Brasileirão Série A", CUP = "Copa do Brasil", LIB = "Copa Libertadores";
    static final List<String> FILES = List.of("Brasileirao_Matches", "Brazilian_Cup_Matches",
        "Libertadores_Matches", "novo_campeonato_brasileiro", "BR-Football-Dataset", "fifa_data");
    final List<Match> matches = new ArrayList<>(), raw = new ArrayList<>();
    final List<Map<String,String>> players = new ArrayList<>();
    final Map<String,Set<String>> clubStates = new HashMap<>();
    final Map<String,String> aliases = new HashMap<>();
    static String fold(String s) {
        return Normalizer.normalize(s, Normalizer.Form.NFD).replaceAll("\\p{M}+", "")
            .toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]+"," ").trim();
    }
    void alias(String display, String... names) {
        aliases.put(fold(display),display);
        for (String s:names) aliases.put(fold(s),display);
    }
    String team(String s) {
        String key = fold(s);
        return aliases.getOrDefault(key,key);
    }
    record Match(LocalDate date, Integer season, String competition, String round, String stage,
                 String home, String away, Integer homeGoals, Integer awayGoals,
                 Map<String,Map<String,String>> sources) {
        boolean played() { return homeGoals != null && awayGoals != null; }
        Match merge(Match other) {
            var provenance = new LinkedHashMap<>(sources);
            provenance.putAll(other.sources);
            return new Match(date,season,competition,round,stage,home,away,
                played()?homeGoals:other.homeGoals,played()?awayGoals:other.awayGoals,provenance);
        }
    }
    SoccerData(Path dir) throws IOException {
        alias("Corinthians","Sport Club Corinthians Paulista");
        alias("Flamengo","CR Flamengo","Clube de Regatas do Flamengo");
        alias("Palmeiras","Sociedade Esportiva Palmeiras");
        alias("São Paulo","São Paulo FC","São Paulo Futebol Clube");
        alias("Atlético-MG","Atlético Mineiro","Atlético Mineiro MG","Clube Atlético Mineiro");
        alias("Athletico-PR","Atletico PR","Atletico Paranaense","Athletico Paranaense","Athletico","Athletico Paranaense PR","Atletico Paranaense PR");
        alias("Atlético-GO","Atletico Goianiense");
        alias("Vasco da Gama","Vasco","Vasco Da Gama RJ");
        alias("Sport","Sport Recife","Sport Club do Recife");
        alias("Bahia","EC Bahia"); alias("Fortaleza","Fortaleza FC","Fortaleza Esporte Clube");
        alias("Juventude","EC Juventude"); alias("Santa Cruz","Santa Cruz FC");
        alias("Red Bull Bragantino","Bragantino","Bragantino SP");
        alias("Botafogo","Botafogo RJ"); alias("América-MG","América Mineiro","América FC (Minas Gerais)");
        for(String s:List.of("Grêmio","Avaí","Goiás","Ceará","Náutico","Criciúma","Paraná","Cuiabá","Vitória","Santos","Fluminense","Internacional")) alias(s);
        read(dir,0,r -> {
            for(String side:List.of("home","away")) {
                String full=r.get(side+"_team"), base=full.replaceFirst("-[A-Z]{2}$","");
                String display=aliases.getOrDefault(fold(full),aliases.getOrDefault(fold(base),base));
                alias(display,full);
            }
        });
        read(dir,1,r->{
            for(String side:List.of("home_team","away_team")) {
                String name=r.get(side);
                int separator=name.lastIndexOf(" - ");
                if(separator>=0) clubStates.computeIfAbsent(fold(name.substring(0,separator)),k->new HashSet<>())
                    .add(name.substring(separator+3));
            }
        });
        var cupFinalDates=new HashSet<LocalDate>();
        var byPair=new HashMap<List<String>,List<Integer>>();
        for(int i=0;i<5;i++) {
            final int source=i;
            if(source==4) {
                // A completed cup ends with two legs of the same tie. Extended rows lack rounds.
                var cupSeasons=new HashMap<Integer,List<Match>>();
                read(dir,4,r->{
                    if(r.get("tournament").equals(CUP)) {
                        Match m=parse(4,r);
                        if(m.season>=2021) cupSeasons.computeIfAbsent(m.season,k->new ArrayList<>()).add(m);
                    }
                });
                for(var fixtures:cupSeasons.values()) {
                    fixtures.sort(Comparator.comparing(Match::date).reversed());
                    if(fixtures.size()<2) continue;
                    Match last=fixtures.get(0), previous=fixtures.get(1);
                    if(last.home.equals(previous.away) && last.away.equals(previous.home)) {
                        cupFinalDates.add(last.date); cupFinalDates.add(previous.date);
                    }
                }
            }
            read(dir,i,r -> {
                Match m=parse(source,r);
                if(source==4 && m.competition.equals(CUP) && cupFinalDates.contains(m.date))
                    m=new Match(m.date,m.season,m.competition,m.round,"final",m.home,m.away,m.homeGoals,m.awayGoals,m.sources);
                raw.add(m);
                var ids=byPair.computeIfAbsent(List.of(m.competition,m.home,m.away),k->new ArrayList<>());
                for(int id:ids) {
                    Match existing=matches.get(id);
                    boolean sameLeague=m.competition.equals(LEAGUE) && Objects.equals(existing.season,m.season);
                    boolean close=m.date!=null && existing.date!=null && Math.abs(existing.date.toEpochDay()-m.date.toEpochDay())<=1;
                    if(!Collections.disjoint(existing.sources.keySet(),m.sources.keySet())) continue;
                    if(close || sameLeague) {
                        matches.set(id,existing.merge(m));
                        return;
                    }
                }
                // The competition-specific file supplies the full fixture list in these years.
                if(source==4 && m.competition.equals(LEAGUE) && m.season>=2012 && m.season<=2022) return;
                if(source==4 && m.competition.equals(CUP) && m.season>=2012 &&
                    (m.season<=2020 || m.season==2021 && !m.date.isAfter(LocalDate.of(2021,8,5)))) return;
                ids.add(matches.size()); matches.add(m);
            });
        }
        read(dir,5,r->players.add(r.toMap()));
        players.sort(Comparator.comparingInt((Map<String,String> p)->Integer.parseInt(p.get("Overall"))).reversed());
        matches.sort(Comparator.comparing(Match::date,Comparator.nullsLast(Comparator.reverseOrder())));
        raw.sort(Comparator.comparing(Match::date,Comparator.nullsLast(Comparator.reverseOrder())));
    }
    static void read(Path dir,int i,Consumer<CSVRecord> consume) throws IOException {
        try(var reader=Files.newBufferedReader(dir.resolve(FILES.get(i)+".csv"));
            var csv=CSVFormat.DEFAULT.builder().setHeader().setSkipHeaderRecord(true).build().parse(reader)) {
            csv.forEach(consume);
        }
    }
    static String competition(String s) {
        return switch(fold(s)) {
            case "serie a","brasileirao","brasileirao serie a","brazilian serie a" -> LEAGUE;
            case "copa do brasil","brazilian cup" -> CUP;
            case "libertadores","copa libertadores" -> LIB;
            default -> s;
        };
    }
    static Integer goals(String s) { return s.matches("[0-9]+(\\.0)?")?(int)Double.parseDouble(s):null; }
    static LocalDate date(String s) {
        return s.contains("/")?LocalDate.parse(s,DateTimeFormatter.ofPattern("dd/MM/uuuu")):LocalDate.parse(s.substring(0,10));
    }
    String club(String name) {
        String key=fold(name);
        String stripped=name.replaceFirst(" - [A-Z]{2}$","");
        if(!aliases.containsKey(key) && !stripped.equals(name) &&
            clubStates.getOrDefault(fold(stripped),Set.of()).size()<=1)
            key=fold(stripped);
        return aliases.computeIfAbsent(key,k->stripped.equals(name)||k.equals(fold(stripped))?stripped:name);
    }
    Match parse(int i, CSVRecord r) {
        boolean history=i==3, extra=i==4;
        String day=r.get(history?"Data":extra?"date":"datetime");
        LocalDate d=day.equals("NA")?null:date(day);
        String year=extra?String.valueOf(d.getYear()):r.get(history?"Ano":"season");
        Integer season=year.equals("NA")?null:Integer.valueOf(year);
        if(extra && season==2021 && (d.getMonthValue()<=2 ||
            r.get("tournament").equals(CUP) && !d.isAfter(LocalDate.of(2021,3,7)))) season=2020;
        String comp=extra?competition(r.get("tournament")):i==1?CUP:i==2?LIB:LEAGUE;
        String round=extra||i==2?"":r.get(history?"Rodada":"round");
        String stage=i==2?r.get("stage"):"";
        if(i==1 && season<=2020 && round.equals(season==2012?"6":season==2016?"7":"8")) stage="final";
        return new Match(d,season,comp,round,stage,club(r.get(history?"Equipe_mandante":extra?"home":"home_team")),
            club(r.get(history?"Equipe_visitante":extra?"away":"away_team")),goals(r.get(history?"Gols_mandante":"home_goal")),
            goals(r.get(history?"Gols_visitante":"away_goal")),Map.of(FILES.get(i),r.toMap()));
    }
}
