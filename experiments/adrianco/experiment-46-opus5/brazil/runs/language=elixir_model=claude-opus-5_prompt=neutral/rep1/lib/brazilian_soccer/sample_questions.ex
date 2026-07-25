defmodule BrazilianSoccer.SampleQuestions do
  @moduledoc """
  The catalogue of questions this server can answer, each mapped to the MCP
  tool call that answers it.

  It is used three ways: as the `brazilian-soccer://sample-questions`
  resource (so a connected model can see what is possible), as the script for
  `mix soccer.demo`, and as the acceptance test in
  `test/sample_questions_test.exs`.
  """

  alias BrazilianSoccer.MCP.Tools

  @questions [
    # --- 1. match queries --------------------------------------------------
    %{
      category: "Match queries",
      question: "Show me all Flamengo vs Fluminense matches",
      tool: "head_to_head",
      arguments: %{"team_a" => "Flamengo", "team_b" => "Fluminense"}
    },
    %{
      category: "Match queries",
      question: "What matches did Palmeiras play in 2023?",
      tool: "search_matches",
      arguments: %{"team" => "Palmeiras", "season" => 2023, "limit" => 10}
    },
    %{
      category: "Match queries",
      question: "Find all Copa do Brasil finals",
      tool: "search_matches",
      arguments: %{"competition" => "Copa do Brasil", "stage" => "final", "limit" => 30}
    },
    %{
      category: "Match queries",
      question: "When did Flamengo last play Corinthians, and what was the score?",
      tool: "last_meeting",
      arguments: %{"team_a" => "Flamengo", "team_b" => "Corinthians"}
    },
    %{
      category: "Match queries",
      question: "Show me all derbies in 2023",
      tool: "find_derbies",
      arguments: %{"season" => 2023}
    },
    %{
      category: "Match queries",
      question: "Which matches did Grêmio play away in the 2019 Libertadores?",
      tool: "search_matches",
      arguments: %{
        "team" => "Grêmio",
        "competition" => "Libertadores",
        "season" => 2019,
        "venue" => "away"
      }
    },

    # --- 2. team queries ---------------------------------------------------
    %{
      category: "Team queries",
      question: "What is Corinthians' home record in 2022?",
      tool: "team_stats",
      arguments: %{
        "team" => "Corinthians",
        "season" => 2022,
        "competition" => "Brasileirão",
        "venue" => "home"
      }
    },
    %{
      category: "Team queries",
      question: "Which team scored the most goals in Série A 2023?",
      tool: "competition_summary",
      arguments: %{"competition" => "Serie A", "season" => 2023}
    },
    %{
      category: "Team queries",
      question: "Compare Palmeiras and Santos head-to-head",
      tool: "compare_teams",
      arguments: %{"team_a" => "Palmeiras", "team_b" => "Santos"}
    },
    %{
      category: "Team queries",
      question: "Which team has the best home record in the Brasileirão?",
      tool: "team_rankings",
      arguments: %{"metric" => "home", "competition" => "Brasileirão", "limit" => 10}
    },
    %{
      category: "Team queries",
      question: "Which team has the best away record?",
      tool: "team_rankings",
      arguments: %{"metric" => "away", "competition" => "Brasileirão", "limit" => 10}
    },
    %{
      category: "Team queries",
      question: "What competitions has Palmeiras played in?",
      tool: "team_profile",
      arguments: %{"team" => "Palmeiras"}
    },
    %{
      category: "Team queries",
      question: "Is \"Atlético\" Mineiro, Goianiense or Paranaense?",
      tool: "resolve_team_name",
      arguments: %{"name" => "Atlético"}
    },

    # --- 3. player queries -------------------------------------------------
    %{
      category: "Player queries",
      question: "Find all Brazilian players in the dataset",
      tool: "players_by_nationality",
      arguments: %{"nationality" => "Brazil", "limit" => 10}
    },
    %{
      category: "Player queries",
      question: "Who are the highest-rated players at Grêmio?",
      tool: "club_squad",
      arguments: %{"club" => "Grêmio"}
    },
    %{
      category: "Player queries",
      question: "Show me all forwards from Santos",
      tool: "search_players",
      arguments: %{"club" => "Santos", "position_group" => "forward"}
    },
    %{
      category: "Player queries",
      question: "Who is Neymar?",
      tool: "player_profile",
      arguments: %{"name" => "Neymar"}
    },
    %{
      category: "Player queries",
      question: "Which players play for Flamengo?",
      tool: "club_squad",
      arguments: %{"club" => "Flamengo"}
    },
    %{
      category: "Player queries",
      question: "Who are the top rated Brazilian players?",
      tool: "search_players",
      arguments: %{"nationality" => "Brazil", "sort_by" => "overall", "limit" => 10}
    },
    %{
      category: "Player queries",
      question: "Which Brazilian goalkeepers are rated 80 or higher?",
      tool: "search_players",
      arguments: %{
        "nationality" => "Brazil",
        "position_group" => "goalkeeper",
        "min_overall" => 80
      }
    },

    # --- 4. competition queries -------------------------------------------
    %{
      category: "Competition queries",
      question: "Who won the 2019 Brasileirão?",
      tool: "competition_champion",
      arguments: %{"competition" => "Brasileirão", "season" => 2019}
    },
    %{
      category: "Competition queries",
      question: "Show the 2019 Brasileirão final standings",
      tool: "league_standings",
      arguments: %{"competition" => "Brasileirão", "season" => 2019}
    },
    %{
      category: "Competition queries",
      question: "Which teams were relegated in 2020?",
      tool: "league_standings",
      arguments: %{"competition" => "Brasileirão", "season" => 2020}
    },
    %{
      category: "Competition queries",
      question: "Show the 2018 Copa Libertadores bracket",
      tool: "cup_bracket",
      arguments: %{"competition" => "Libertadores", "season" => 2018}
    },
    %{
      category: "Competition queries",
      question: "Who won the 2019 Copa do Brasil?",
      tool: "competition_champion",
      arguments: %{"competition" => "Copa do Brasil", "season" => 2019}
    },
    %{
      category: "Competition queries",
      question: "Which competitions and seasons are covered?",
      tool: "list_competitions",
      arguments: %{}
    },

    # --- 5. statistical analysis ------------------------------------------
    %{
      category: "Statistical analysis",
      question: "What's the average goals per match in the Brasileirão?",
      tool: "match_statistics",
      arguments: %{"competition" => "Brasileirão"}
    },
    %{
      category: "Statistical analysis",
      question: "Show me the biggest wins in the dataset",
      tool: "biggest_wins",
      arguments: %{"limit" => 10}
    },
    %{
      category: "Statistical analysis",
      question: "What were the highest scoring matches in the Brasileirão?",
      tool: "highest_scoring_matches",
      arguments: %{"competition" => "Brasileirão", "limit" => 5}
    },
    %{
      category: "Statistical analysis",
      question: "Compare the 2018 and 2019 seasons",
      tool: "compare_seasons",
      arguments: %{"competition" => "Brasileirão", "seasons" => [2018, 2019]}
    },
    %{
      category: "Statistical analysis",
      question: "How big is home advantage in the Brasileirão?",
      tool: "home_advantage",
      arguments: %{"competition" => "Brasileirão"}
    },
    %{
      category: "Statistical analysis",
      question: "What data is loaded into the knowledge graph?",
      tool: "list_datasets",
      arguments: %{}
    }
  ]

  @doc "Every sample question with the tool call that answers it."
  @spec all() :: [map]
  def all, do: @questions

  @doc "Sample questions grouped by category."
  @spec by_category() :: [{binary, [map]}]
  def by_category do
    @questions
    |> Enum.group_by(& &1.category)
    |> Enum.sort_by(fn {category, _} -> category end)
  end

  @doc "Answer one sample question through the MCP tool layer."
  @spec answer(map) :: {:ok, binary} | {:error, binary}
  def answer(%{tool: tool, arguments: arguments}) do
    case Tools.call(tool, arguments) do
      {:ok, %{text: text}} -> {:ok, text}
      {:error, message} -> {:error, message}
    end
  end

  @doc "Markdown listing, used as the `sample-questions` MCP resource."
  @spec markdown() :: binary
  def markdown do
    body =
      Enum.map_join(by_category(), "\n\n", fn {category, questions} ->
        lines =
          Enum.map_join(questions, "\n", fn question ->
            "- #{question.question} → `#{question.tool}` #{inspect(question.arguments)}"
          end)

        "## #{category}\n#{lines}"
      end)

    "# Questions this server can answer\n\n#{body}\n"
  end
end
