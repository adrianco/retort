package soccer;

import java.text.Normalizer;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

final class Names {
    private static final Map<String, String> ALIASES = new HashMap<>();

    static {
        aliases("Flamengo", "Flamengo RJ", "Clube de Regatas do Flamengo", "CR Flamengo");
        aliases("Fluminense", "Fluminense RJ", "Fluminense FC");
        aliases("Palmeiras", "Palmeiras SP", "Sociedade Esportiva Palmeiras", "SE Palmeiras");
        aliases("Corinthians", "Corinthians SP", "Sport Club Corinthians Paulista", "Corinthians Paulista");
        aliases("São Paulo", "São Paulo SP", "São Paulo FC", "São Paulo Futebol Clube", "SPFC");
        aliases("Santos", "Santos SP", "Santos FC", "Santos Futebol Clube");
        aliases("Vasco", "Vasco RJ", "Vasco da Gama RJ", "Vasco da Gama", "CR Vasco da Gama");
        aliases("Botafogo-RJ", "Botafogo", "Botafogo de Futebol e Regatas");
        aliases("Grêmio", "Grêmio RS", "Grêmio Foot-Ball Porto Alegrense");
        aliases("Internacional", "Internacional RS", "Sport Club Internacional", "SC Internacional");
        aliases("Athletico-PR", "Athletico", "Athletico Paranaense", "Atletico Paranaense",
                "Atlético Paranaense PR", "Atlético PR", "Athletico Paranaense PR", "Club Athletico Paranaense");
        aliases("Atlético-MG", "Atlético Mineiro", "Atlético Mineiro MG", "Clube Atlético Mineiro");
        aliases("Atlético-GO", "Atlético Goianiense", "Atlético Goianiense GO", "Atlético Clube Goianiense");
        aliases("América-MG", "América FC Minas Gerais", "América Mineiro");
        aliases("América-RN", "América FC Natal", "América de Natal");
        aliases("Flamengo-PI", "Flamengo do Piauí PI");
        aliases("Fluminense de Feira", "Fluminense de Feira BA");
        aliases("Atlético-CE", "FC Atlético Cearense", "Atlético Cearense CE");
        aliases("Atlético-AC", "Atlético Acreano");
        aliases("Atlético-BA", "Atlético Alagoinhas");
        aliases("Sport", "Sport PE", "Sport Recife", "Sport Club do Recife");
        aliases("Ceará", "Ceará CE", "Ceará Sporting Club");
        for (String pair : new String[]{"Bahia BA", "Vitória BA", "Cruzeiro MG", "Chapecoense SC", "Paraná PR",
                "Coritiba PR", "Cuiabá MT", "Juventude RS", "Fortaleza CE", "Goiás GO", "Avaí SC",
                "Figueirense SC", "Criciúma SC", "Ponte Preta SP", "Bragantino SP", "Guarani SP",
                "Portuguesa SP", "Náutico PE", "Santa Cruz PE", "Vila Nova GO", "Paysandu PA",
                "Remo PA", "Ceará CE", "CSA AL", "CRB AL", "ABC RN", "Joinville SC",
                "Oeste SP", "Ituano SP", "Londrina PR", "Sampaio Corrêa MA", "Operário PR"}) {
            aliases(pair.substring(0, pair.lastIndexOf(' ')), pair);
        }
        aliases("Bragantino", "Red Bull Bragantino", "Red Bull Bragantino SP", "RB Bragantino");
        aliases("Bahia", "EC Bahia", "Esporte Clube Bahia");
        aliases("Fortaleza", "Fortaleza FC", "Fortaleza Esporte Clube");
        aliases("Santa Cruz", "Santa Cruz FC");
        aliases("Juventude", "EC Juventude");
        aliases("Operário", "Operário Ferroviário", "Operário Ferroviário PR");
    }

    private static void aliases(String name, String... variants) {
        ALIASES.put(fold(name), name);
        for (String variant : variants) {
            ALIASES.put(fold(variant), name);
        }
    }

    static String fold(String name) {
        return Normalizer.normalize(name, Normalizer.Form.NFD).replaceAll("\\p{M}+", "")
                .toLowerCase(Locale.ROOT).replaceAll("[^\\p{L}\\p{N}]+", " ").strip();
    }

    static String team(String name) {
        return ALIASES.getOrDefault(fold(name), name.strip());
    }

    static String teamKey(String name) {
        return fold(team(name));
    }

    static String competition(String name) {
        return switch (fold(name)) {
            case "brasileirao", "brasileirao serie a", "brasileirao serie a matches", "serie a",
                    "campeonato brasileiro", "campeonato brasileiro serie a" -> "Brasileirão";
            case "copa do brasil", "brazilian cup" -> "Copa do Brasil";
            case "libertadores", "copa libertadores", "conmebol libertadores" -> "Libertadores";
            case "serie b", "brasileirao serie b" -> "Série B";
            case "serie c", "brasileirao serie c" -> "Série C";
            default -> name.strip();
        };
    }

    private Names() {}
}
