package com.brazilsoccer.mcp.tools;

import com.brazilsoccer.mcp.McpServerFactory;
import com.brazilsoccer.mcp.support.TestFixtures;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Contract of the tool catalogue: naming, schemas and error handling. */
class ToolCatalogTest {

    private final ToolRegistry registry = TestFixtures.registry();

    @Test
    @DisplayName("every capability of the specification is covered by a tool")
    void coversEveryRequiredCapability() {
        assertThat(registry.tools()).extracting(SoccerTool::name).contains(
                "search_matches", "head_to_head", "find_derbies",          // match queries
                "team_stats", "team_competitions", "list_teams",           // team queries
                "search_players", "player_profile", "player_club_summary", // player queries
                "standings", "competition_summary", "compare_seasons",     // competition queries
                "statistics",                                              // statistical analysis
                "player_club_report",                                      // cross-file query
                "dataset_info");                                           // introspection
    }

    @Test
    @DisplayName("tool metadata is complete and MCP compatible")
    void exposesValidSchemas() {
        for (SoccerTool tool : registry.tools()) {
            assertThat(tool.name()).matches("[a-z][a-z0-9_]*");
            assertThat(tool.title()).isNotBlank();
            assertThat(tool.description()).isNotBlank();
            assertThat(tool.inputSchema()).containsEntry("type", "object");
            assertThat(tool.inputSchema()).containsKeys("properties", "required");

            @SuppressWarnings("unchecked")
            Map<String, Object> properties = (Map<String, Object>) tool.inputSchema().get("properties");
            @SuppressWarnings("unchecked")
            List<String> required = (List<String>) tool.inputSchema().get("required");
            assertThat(properties.keySet()).containsAll(required);
        }
    }

    @Test
    @DisplayName("the MCP adapter converts every tool into a tool specification")
    void adaptsToMcpSpecifications() {
        assertThat(McpServerFactory.toolSpecifications(registry))
                .hasSize(registry.tools().size())
                .allSatisfy(specification -> assertThat(specification.tool().name()).isNotBlank());
    }

    @Test
    void rejectsUnknownTools() {
        assertThatThrownBy(() -> registry.call("no_such_tool", Map.of()))
                .isInstanceOf(ToolException.class)
                .hasMessageContaining("Unknown tool")
                .hasMessageContaining("search_matches");
    }

    @Test
    @DisplayName("argument problems produce actionable messages instead of stack traces")
    void reportsArgumentProblems() {
        assertThatThrownBy(() -> registry.call("team_stats", Map.of()))
                .isInstanceOf(ToolException.class)
                .hasMessageContaining("team");

        assertThatThrownBy(() -> registry.call("team_stats", Map.of("team", "Zzz Unknown FC")))
                .isInstanceOf(ToolException.class)
                .hasMessageContaining("No club matching");

        assertThatThrownBy(() -> registry.call("standings", Map.of("season", 1899)))
                .isInstanceOf(ToolException.class)
                .hasMessageContaining("Available seasons");

        assertThatThrownBy(() -> registry.call("search_matches", Map.of("competition", "premier league")))
                .isInstanceOf(ToolException.class)
                .hasMessageContaining("Unknown competition");

        assertThatThrownBy(() -> registry.call("search_matches", Map.of("season", "nineteen")))
                .isInstanceOf(ToolException.class)
                .hasMessageContaining("must be a number");
    }

    @Test
    @DisplayName("string arguments are accepted where numbers are expected, as LLM clients do")
    void acceptsLooselyTypedArguments() {
        String fromStrings = registry.call("standings", Map.of("season", "2019", "limit", "3"));
        String fromNumbers = registry.call("standings", Map.of("season", 2019, "limit", 3));

        assertThat(fromStrings).isEqualTo(fromNumbers).contains("Flamengo");
    }
}
