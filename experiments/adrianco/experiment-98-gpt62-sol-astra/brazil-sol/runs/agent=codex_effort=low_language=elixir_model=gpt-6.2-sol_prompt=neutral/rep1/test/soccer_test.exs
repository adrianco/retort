defmodule SoccerTest do
  use ExUnit.Case, async: true

  alias Soccer.{Data, MCP}

  setup_all do
    {:ok, data: Data.load!(Path.expand("../data/kaggle", __DIR__))}
  end

  describe "given the supplied datasets and an MCP client" do
    test "discovers tools after negotiating a protocol version", %{data: data} do
      assert %{result: %{protocolVersion: "2025-11-25", capabilities: %{tools: %{}}}} =
               request(data, "initialize", %{"protocolVersion" => "2025-11-25"})

      assert %{result: %{protocolVersion: "2024-11-05"}} =
               request(data, "initialize", %{"protocolVersion" => "2024-11-05"})

      assert nil ==
               MCP.handle(data, %{"jsonrpc" => "2.0", "method" => "notifications/initialized"})

      assert %{result: %{tools: tools}} = request(data, "tools/list")

      assert Enum.sort(Enum.map(tools, & &1.name)) ==
               ~w(competition data_sources find_matches find_players statistics team_profile)
    end

    test "loads and queries all six files", %{data: data} do
      expected = %{
        "Brasileirao_Matches.csv" => 4180,
        "Brazilian_Cup_Matches.csv" => 1337,
        "Libertadores_Matches.csv" => 1255,
        "BR-Football-Dataset.csv" => 10296,
        "novo_campeonato_brasileiro.csv" => 6886,
        "fifa_data.csv" => 18207
      }

      assert call(data, "data_sources").row_counts == expected

      for {source, count} <- Map.delete(expected, "fifa_data.csv") do
        assert %{matches: [%{sources: [^source]}], total: ^count} =
                 call(data, "find_matches", %{"source" => source, "limit" => 1})
      end

      assert %{total: 18207, players: [%{name: "Cristiano Ronaldo"}]} =
               call(data, "find_players", %{"limit" => 1})
    end

    test "returns errors for invalid requests and continues serving queries", %{data: data} do
      assert %{error: %{code: -32700}} = MCP.handle_line(data, "{")
      assert %{error: %{code: -32600}} = MCP.handle_line(data, "[]")
      assert %{error: %{code: -32601}} = request(data, "missing")
      assert %{error: %{code: -32602}} = request(data, "tools/call", %{"name" => "missing"})

      for {name, args} <- [
            {"find_matches", %{"opponent" => "Santos"}},
            {"find_matches", %{"limit" => 0}},
            {"find_matches", %{"from" => "31/02/2020"}},
            {"find_matches", %{"from" => "2020-05-01", "to" => "2020-01-01"}},
            {"find_matches", %{"season" => "2019"}},
            {"team_profile", %{}}
          ] do
        assert %{result: %{isError: true, content: [%{type: "text"}]}} =
                 request(data, "tools/call", %{"name" => name, "arguments" => args})
      end

      assert %{result: %{}} = request(data, "ping")
    end
  end

  describe "match and team questions" do
    test "shows Flamengo vs Fluminense with scores and reciprocal head-to-head records", %{
      data: data
    } do
      response =
        call(data, "find_matches", %{"team" => "Flamengo-RJ", "opponent" => "Fluminense FC"})

      assert response.total > 20
      assert [%{wins: wins, draws: draws, goals_for: goals}, opponent] = response.head_to_head
      assert {opponent.losses, opponent.draws, opponent.goals_against} == {wins, draws, goals}

      assert Enum.all?(response.matches, fn m ->
               Enum.sort([m.home_team, m.away_team]) == ["Flamengo", "Fluminense"] and
                 is_binary(m.date) and is_integer(m.home_goal) and is_integer(m.away_goal) and
                 is_binary(m.competition)
             end)
    end

    test "finds the latest Flamengo–Corinthians match and its score", %{data: data} do
      args = %{
        "team" => "Flamengo",
        "opponent" => "Sport Club Corinthians Paulista",
        "limit" => 1
      }

      assert %{matches: [%{home_goal: 1, away_goal: 1, date: "2023-10-08"}], next_offset: 1} =
               call(data, "find_matches", args)

      assert %{matches: [%{date: earlier}]} =
               call(data, "find_matches", Map.put(args, "offset", 1))

      assert earlier < "2023-10-08"
    end

    test "lists the matches Palmeiras played in 2023", %{data: data} do
      args = %{"team" => "Palmeiras", "season" => 2023, "limit" => 100}
      result = call(data, "find_matches", args)
      assert result.total > 37
      assert Enum.all?(result.matches, &(&1.season == 2023))
    end

    test "finds all Copa do Brasil finals and preserves the 2020 edition's date", %{data: data} do
      result =
        call(data, "find_matches", %{
          "competition" => "Copa do Brasil",
          "stage" => "finals",
          "limit" => 50
        })

      assert result.total == 24

      assert Enum.any?(
               result.matches,
               &(&1.season == 2020 and String.starts_with?(&1.date, "2021"))
             )

      assert Enum.count(result.matches, &(&1.season == 2021)) == 2
    end

    test "filters dates in Brazilian and ISO formats", %{data: data} do
      assert %{
               total: 1,
               matches: [
                 %{date: "2003-03-29", home_goal: 4, away_goal: 2, stadium: "Brinco de Ouro"}
               ]
             } =
               call(data, "find_matches", %{
                 "team" => "Guarani-SP",
                 "venue" => "home",
                 "from" => "29/03/2003",
                 "to" => "2003-03-29"
               })
    end

    test "finds traditional derbies in 2023", %{data: data} do
      result = call(data, "find_matches", %{"season" => 2023, "derbies" => true, "limit" => 200})
      assert result.total > 20

      assert Enum.any?(
               result.matches,
               &(&1.home_team == "São Paulo" and &1.away_team == "Palmeiras")
             )

      refute Enum.any?(result.matches, &(&1.home_team == "Cuiabá" or &1.away_team == "Cuiabá"))
    end

    test "calculates Corinthians' 2022 Série A home record", %{data: data} do
      args = %{
        "team" => "Corinthians-SP",
        "venue" => "home",
        "competition" => "Série A",
        "season" => 2022
      }

      assert %{
               record: %{played: 19, wins: wins, draws: draws, losses: losses, goals_for: goals},
               away: %{played: 0}
             } =
               call(data, "team_profile", args)

      assert wins + draws + losses == 19
      assert goals > 0
    end

    test "lists competitions Palmeiras played in and summarizes performance by season", %{
      data: data
    } do
      result =
        call(data, "team_profile", %{"team" => "Sociedade Esportiva Palmeiras", "limit" => 1})

      assert Enum.map(result.by_competition, & &1.competition) ==
               ["Brasileirão Série A", "Copa Libertadores", "Copa do Brasil"]

      assert Enum.any?(result.by_season, &(&1.season == 2023 and &1.wins > 0))
    end

    test "compares Palmeiras and Santos", %{data: data} do
      result =
        call(data, "find_matches", %{
          "team" => "Palmeiras",
          "opponent" => "Santos FC",
          "limit" => 1
        })

      assert [%{team: "Palmeiras", played: games}, %{team: "Santos", played: games}] =
               result.head_to_head

      assert games > 30
    end

    test "links Grêmio's FIFA roster with its match history", %{data: data} do
      assert %{fifa_roster: %{total: 20, players: [%{club: "Grêmio"}]}, record: %{played: played}} =
               call(data, "team_profile", %{"team" => "Gremio-RS", "limit" => 1})

      assert played > 500
    end
  end

  describe "player questions" do
    test "finds Brazilian players, ordered by overall", %{data: data} do
      assert %{total: 827, players: [%{name: "Neymar Jr", overall: 92, position: "LW"}]} =
               call(data, "find_players", %{"nationality" => "Brazilian", "limit" => 1})
    end

    test "looks up a player and returns skill and physical attributes", %{data: data} do
      assert %{
               players: [
                 %{name: "Neymar Jr", attributes: %{"Dribbling" => "96", "Height" => height}}
               ]
             } =
               call(data, "find_players", %{"name" => "NEYMAR", "attributes" => true})

      assert height != ""
    end

    test "ranks a club's forwards and reports empty results when a club is missing", %{data: data} do
      assert %{players: [_ | _] = forwards} =
               call(data, "find_players", %{
                 "club" => "Atlético Mineiro-MG",
                 "position" => "forwards"
               })

      assert Enum.all?(forwards, &(&1.position in ~w(ST CF LF RF LS RS LW RW)))

      assert Enum.map(forwards, & &1.overall) ==
               Enum.sort(Enum.map(forwards, & &1.overall), :desc)

      assert %{total: 0, players: []} = call(data, "find_players", %{"club" => "Flamengo"})
    end

    test "summarizes Brazilian FIFA players at domestic clubs", %{data: data} do
      result =
        call(data, "find_players", %{
          "nationality" => "Brazil",
          "brazilian_clubs" => true,
          "limit" => 1
        })

      assert Enum.any?(
               result.by_club,
               &(&1.club == "Grêmio" and &1.players == 20 and &1.average_overall > 0)
             )

      refute Enum.any?(result.by_club, &(&1.club == "Paris Saint-Germain"))
    end
  end

  describe "competition and statistical questions" do
    test "calculates 2019 standings and identifies the champion", %{data: data} do
      args = %{"competition" => "Brasileirão", "season" => 2019}

      assert %{
               standings: [%{team: "Flamengo", points: 90}, %{team: "Santos", points: 74} | rest],
               complete: true
             } =
               call(data, "competition", args)

      assert length(rest) == 18

      assert %{champion: %{team: "Flamengo", wins: 28, draws: 6, losses: 4}} =
               call(data, "competition", Map.put(args, "view", "champion"))
    end

    test "lists the 2020 relegation places", %{data: data} do
      result =
        call(data, "competition", %{
          "competition" => "Serie A",
          "season" => 2020,
          "view" => "relegation"
        })

      assert result.complete

      assert Enum.map(result.relegated, & &1.team) == [
               "Vasco da Gama",
               "Goiás",
               "Coritiba",
               "Botafogo"
             ]
    end

    test "shows the 2018 Libertadores bracket", %{data: data} do
      result =
        call(data, "competition", %{
          "competition" => "Libertadores",
          "season" => 2018,
          "view" => "bracket"
        })

      assert Enum.map(result.stages, & &1.stage) == [
               "group stage",
               "round of 16",
               "quarterfinals",
               "semifinals",
               "final"
             ]

      assert length(List.last(result.stages).matches) == 2
    end

    test "returns competition results and details from the extended source", %{data: data} do
      assert %{
               total: 2,
               matches: [%{statistics: %{"total_corners" => 6}, home_goal: 1, away_goal: 1}]
             } =
               call(data, "competition", %{
                 "competition" => "Copa do Brasil",
                 "season" => 2023,
                 "view" => "results",
                 "stage" => "final",
                 "limit" => 1
               })
    end

    test "flags incomplete standings and the absence of goalscorer events", %{data: data} do
      args = %{"competition" => "Serie A", "season" => 2023}

      assert %{complete: false, champion: nil} =
               call(data, "competition", Map.put(args, "view", "champion"))

      assert %{note: note} = call(data, "competition", Map.put(args, "view", "top_scorers"))
      assert note =~ "Player goal totals cannot be determined"
    end

    test "calculates average goals and win rates with the full league data", %{data: data} do
      result = call(data, "statistics", %{"competition" => "Brasileirão", "season" => 2019})
      assert result.played == 380
      assert result.average_goals == 2.31
      assert result.home_wins + result.away_wins + result.draws == 380
    end

    test "compares the 2018 and 2019 seasons", %{data: data} do
      assert %{seasons: [%{season: 2018, played: 380}, %{season: 2019, played: 380}]} =
               call(data, "statistics", %{
                 "competition" => "Série A",
                 "seasons" => [2018, 2019],
                 "view" => "seasons"
               })
    end

    test "ranks clubs by home record, away record or goals scored", %{data: data} do
      for {view, sorting} <- [
            {"best_home", :win_rate},
            {"best_away", :win_rate},
            {"most_goals", :goals_for}
          ] do
        result =
          call(data, "statistics", %{
            "view" => view,
            "competition" => "Série A",
            "season" => 2023,
            "min_matches" => 10
          })

        values = Enum.map(result.teams, &Map.fetch!(&1, sorting))
        assert length(values) == 20
        assert values == Enum.sort(values, :desc)
      end
    end

    test "lists the biggest wins by goal margin", %{data: data} do
      result = call(data, "statistics", %{"view" => "biggest_wins", "limit" => 5})
      margins = Enum.map(result.matches, & &1.margin)
      assert length(margins) == 5
      assert Enum.max(margins) >= 8
      assert margins == Enum.sort(margins, :desc)
    end

    test "serves warmed lookups under two seconds and aggregate queries under five", %{data: data} do
      {lookup, _} =
        :timer.tc(fn -> call(data, "find_matches", %{"team" => "Flamengo", "limit" => 1}) end)

      {aggregate, _} =
        :timer.tc(fn ->
          call(data, "statistics", %{"view" => "best_away", "min_matches" => 10})
        end)

      assert lookup < 2_000_000
      assert aggregate < 5_000_000
    end
  end

  defp request(data, method, params \\ %{}) do
    line = JSON.encode!(%{jsonrpc: "2.0", id: 42, method: method, params: params})
    MCP.handle_line(data, line)
  end

  defp call(data, name, arguments \\ %{}) do
    assert %{id: 42, result: %{structuredContent: result, content: [%{type: "text", text: text}]}} =
             request(data, "tools/call", %{"name" => name, "arguments" => arguments})

    assert JSON.decode!(text) == JSON.decode!(JSON.encode!(result))
    result
  end
end
