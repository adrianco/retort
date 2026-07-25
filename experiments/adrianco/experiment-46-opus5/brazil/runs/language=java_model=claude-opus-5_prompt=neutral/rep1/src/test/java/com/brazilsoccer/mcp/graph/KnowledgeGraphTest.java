package com.brazilsoccer.mcp.graph;

import com.brazilsoccer.mcp.model.Competition;
import com.brazilsoccer.mcp.model.Match;
import com.brazilsoccer.mcp.model.Player;
import com.brazilsoccer.mcp.model.Team;
import com.brazilsoccer.mcp.query.CompetitionService;
import com.brazilsoccer.mcp.query.Venue;
import com.brazilsoccer.mcp.support.TestFixtures;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/** Verifies that the six CSV files end up in one coherent, de-duplicated graph. */
class KnowledgeGraphTest {

    private final KnowledgeGraph graph = TestFixtures.graph();

    @Test
    @DisplayName("all six datasets are loaded and contribute records")
    void loadsEveryDataset() {
        assertThat(graph.datasets()).hasSize(6);
        assertThat(graph.datasets()).allSatisfy(dataset ->
                assertThat(dataset.rowsRead()).as(dataset.fileName()).isGreaterThan(1000));
        assertThat(graph.matches()).hasSizeGreaterThan(15000);
        assertThat(graph.players()).hasSize(18207);
        assertThat(graph.teamCount()).isGreaterThan(500);
    }

    @Test
    @DisplayName("every competition of the specification is queryable")
    void coversEveryCompetition() {
        assertThat(graph.seasons(Competition.SERIE_A)).contains(2003, 2012, 2019, 2022, 2023);
        assertThat(graph.seasons(Competition.SERIE_B)).isNotEmpty();
        assertThat(graph.seasons(Competition.SERIE_C)).isNotEmpty();
        assertThat(graph.seasons(Competition.COPA_DO_BRASIL)).contains(2012, 2019, 2023);
        assertThat(graph.seasons(Competition.LIBERTADORES)).contains(2013, 2019, 2022);
    }

    @Test
    @DisplayName("overlapping files are merged: a league season has each fixture exactly once")
    void mergesOverlappingSources() {
        // 2014-2019 is present in all three Série A files; without merging these seasons would
        // hold up to three copies of every match.
        for (int season : List.of(2014, 2015, 2016, 2017, 2018, 2019)) {
            List<Match> matches = graph.matchesOf(Competition.SERIE_A, season);

            Set<String> fixtures = new HashSet<>();
            for (Match match : matches) {
                assertThat(fixtures.add(match.homeTeamId() + "|" + match.awayTeamId()))
                        .as("duplicate fixture in " + season + ": " + match)
                        .isTrue();
            }
        }
        // A complete double round robin between 20 clubs; 2015 carries one extra row that the
        // source file mislabels as Série A (a Brasília vs CA Taguatinga regional match).
        assertThat(graph.matchesOf(Competition.SERIE_A, 2018)).hasSize(380);
        assertThat(graph.matchesOf(Competition.SERIE_A, 2019)).hasSize(380);
        assertThat(graph.matchesOf(Competition.SERIE_A, 2022)).hasSize(380);
    }

    @Test
    @DisplayName("merging enriches a fixture with the fields of the other sources")
    void mergingEnrichesFixtures() {
        List<Match> matches = graph.matchesOf(Competition.SERIE_A, 2018);

        assertThat(matches).anySatisfy(match -> {
            assertThat(match.sources()).hasSizeGreaterThan(1);
            assertThat(match.round()).isNotNull();
            assertThat(match.arena()).isNotNull();
            assertThat(match.stats()).isNotNull();
        });
    }

    @Test
    @DisplayName("the 2019 Série A table matches the real world result")
    void computesKnownSeasonTable() {
        List<CompetitionService.StandingRow> table =
                new CompetitionService(graph).standings(Competition.SERIE_A, 2019, Venue.ALL);

        assertThat(table).hasSize(20);
        assertThat(graph.nameOf(table.get(0).teamId())).isEqualTo("Flamengo");
        assertThat(table.get(0).record().points()).isEqualTo(90);
        assertThat(table.get(0).record().played()).isEqualTo(38);
        assertThat(graph.nameOf(table.get(1).teamId())).isEqualTo("Santos");
        assertThat(table.get(1).record().points()).isEqualTo(74);
        assertThat(graph.nameOf(table.get(19).teamId())).isEqualTo("Avaí");
    }

    @Test
    @DisplayName("club name variants collapse onto one node, namesakes stay apart")
    void normalisesTeamNames() {
        TeamRegistry registry = graph.registry();
        String flamengo = registry.resolve("Flamengo").orElseThrow().id();

        assertThat(registry.resolve("Flamengo-RJ").orElseThrow().id()).isEqualTo(flamengo);
        assertThat(registry.resolve("flamengo rj").orElseThrow().id()).isEqualTo(flamengo);

        String mineiro = registry.resolve("Atletico Mineiro").orElseThrow().id();
        String paranaense = registry.resolve("Athletico Paranaense").orElseThrow().id();
        String goianiense = registry.resolve("Atletico Goianiense").orElseThrow().id();
        assertThat(registry.resolve("Atlético-MG").orElseThrow().id()).isEqualTo(mineiro);
        assertThat(registry.resolve("Athletico-PR").orElseThrow().id()).isEqualTo(paranaense);
        assertThat(Set.of(mineiro, paranaense, goianiense)).hasSize(3);
    }

    @Test
    @DisplayName("accented display names survive the UTF-8 round trip")
    void keepsPortugueseCharacters() {
        assertThat(graph.registry().resolve("Gremio").orElseThrow().displayName()).isEqualTo("Grêmio");
        assertThat(graph.registry().resolve("Sao Paulo").orElseThrow().displayName()).isEqualTo("São Paulo");
        assertThat(graph.registry().resolve("Avai").orElseThrow().displayName()).isEqualTo("Avaí");
    }

    @Test
    @DisplayName("matches are indexed per club and per competition season")
    void indexesAdjacency() {
        Team flamengo = graph.registry().resolve("Flamengo").orElseThrow();
        List<Match> matches = graph.matchesOf(flamengo.id());

        assertThat(matches).hasSizeGreaterThan(800);
        assertThat(matches).allSatisfy(match -> assertThat(match.involves(flamengo.id())).isTrue());
        assertThat(matches).isSortedAccordingTo((a, b) -> {
            if (a.date() == null || b.date() == null) {
                return 0;
            }
            return a.date().compareTo(b.date());
        });
    }

    @Test
    @DisplayName("players are linked to the same club nodes as the match data")
    void linksPlayersToClubs() {
        Optional<Team> gremio = graph.registry().resolve("Grêmio");
        assertThat(gremio).isPresent();

        List<Player> squad = graph.playersOfClub(gremio.get().id());
        assertThat(squad).isNotEmpty();
        assertThat(graph.matchesOf(gremio.get().id())).isNotEmpty();
        assertThat(squad).isSortedAccordingTo((a, b) -> Integer.compare(b.overall(), a.overall()));

        assertThat(graph.playersOfNationality("Brazil")).hasSize(827);
    }

    @Test
    @DisplayName("the graph exposes node and edge counts")
    void exposesGraphShape() {
        assertThat(graph.edgeCount()).isGreaterThan(graph.matches().size() * 3L);
        assertThat(graph.report().rawMatchRows()).isGreaterThan(graph.matches().size());
        assertThat(graph.report().mergedDuplicates()).isGreaterThan(0);
    }
}
