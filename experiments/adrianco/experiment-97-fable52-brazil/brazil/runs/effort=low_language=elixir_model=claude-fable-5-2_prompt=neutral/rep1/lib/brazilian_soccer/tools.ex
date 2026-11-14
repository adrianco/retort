defmodule BrazilianSoccer.Tools do
  @moduledoc """
  MCP tool catalogue: JSON-schema definitions (`list/0`) and execution
  (`call/3`), which returns `{:ok, text}` or `{:error, message}`.
  """

  alias BrazilianSoccer.{Data, Format, Queries, Text}

  @str %{"type" => "string"}
  @int %{"type" => "integer"}

  @match_filters %{
    "competition" =>
      Map.put(
        @str,
        "description",
        "Brasileirão (Série A), Série B, Série C, Copa do Brasil or Libertadores"
      ),
    "season" => Map.put(@int, "description", "Season year, e.g. 2019"),
    "date_from" => Map.put(@str, "description", "Earliest date, YYYY-MM-DD or DD/MM/YYYY"),
    "date_to" => Map.put(@str, "description", "Latest date, YYYY-MM-DD or DD/MM/YYYY")
  }
  @venue %{
    "type" => "string",
    "enum" => ["home", "away", "any"],
    "description" => "Restrict to the team's home or away matches"
  }
  @limit Map.put(@int, "description", "Maximum rows to list")

  def list do
    [
      tool(
        "search_matches",
        "Find matches by team, opponent, competition, season, date range, round or stage (e.g. stage \"final\"). Newest first. With team and opponent it also reports the head-to-head record.",
        Map.merge(@match_filters, %{
          "team" =>
            Map.put(
              @str,
              "description",
              "Team name; variations such as Palmeiras-SP, Gremio, Atlético Mineiro are accepted"
            ),
          "opponent" =>
            Map.put(@str, "description", "Second team, for matches between two teams"),
          "venue" => @venue,
          "round" => Map.put(@str, "description", "Round number, or a stage name"),
          "stage" =>
            Map.put(
              @str,
              "description",
              "Knockout stage: group stage, round of 16, quarterfinals, semifinals, final"
            ),
          "limit" => @limit
        })
      ),
      tool(
        "head_to_head",
        "Compare two teams head-to-head: wins, draws, goals and the most recent meetings.",
        Map.merge(@match_filters, %{"team_a" => @str, "team_b" => @str, "limit" => @limit}),
        ["team_a", "team_b"]
      ),
      tool(
        "team_stats",
        "Win/draw/loss record, goals and win rate for a team, overall and split home/away and by competition. Filter by season, competition, venue or dates.",
        Map.merge(@match_filters, %{"team" => @str, "venue" => @venue}),
        ["team"]
      ),
      tool(
        "team_profile",
        "Cross-dataset team profile: competitions and seasons played, overall record, latest results and the club's players in the FIFA dataset.",
        %{"team" => @str},
        ["team"]
      ),
      tool(
        "standings",
        "League table for a Série A/B/C season calculated from match results, marking the champion and relegated teams.",
        %{
          "competition" => Map.put(@str, "description", "League (default Brasileirão Série A)"),
          "season" => @int,
          "limit" => @limit
        },
        ["season"]
      ),
      tool(
        "knockout_bracket",
        "Results of a Copa do Brasil or Copa Libertadores season grouped by round/stage, with the champion when the final is decided on aggregate.",
        %{"competition" => @str, "season" => @int},
        ["competition", "season"]
      ),
      tool(
        "team_rankings",
        "Rank teams by a metric over the filtered matches, e.g. best home record, best away record, most goals scored in a season.",
        Map.merge(@match_filters, %{
          "metric" => %{
            "type" => "string",
            "enum" =>
              ~w(win_rate points_per_game points wins draws losses goals_for goals_against goal_difference matches),
            "description" => "Default win_rate"
          },
          "venue" => @venue,
          "order" => %{"type" => "string", "enum" => ["desc", "asc"]},
          "min_matches" =>
            Map.put(@int, "description", "Minimum matches for a team to be ranked"),
          "limit" => @limit
        })
      ),
      tool(
        "biggest_wins",
        "Matches with the largest winning margins, optionally filtered by team, competition, season or dates.",
        Map.merge(@match_filters, %{"team" => @str, "limit" => @limit})
      ),
      tool(
        "competition_stats",
        "Aggregate statistics: matches, goals, average goals per match, home/draw/away rates. Pass several seasons to compare them side by side.",
        Map.merge(@match_filters, %{
          "team" => @str,
          "seasons" => %{
            "type" => "array",
            "items" => @int,
            "description" => "Seasons to compare"
          }
        })
      ),
      tool(
        "derbies",
        "Matches between traditional rivals (Fla-Flu, Derby Paulista, Grenal, ...), filtered by season, competition, team or dates.",
        Map.merge(@match_filters, %{"team" => @str, "limit" => @limit})
      ),
      tool(
        "search_players",
        "Search the FIFA player dataset by name, nationality, club, position (code like ST, or forward/midfielder/defender/goalkeeper) and rating.",
        %{
          "name" => @str,
          "nationality" => Map.put(@str, "description", "e.g. Brazil"),
          "club" => Map.put(@str, "description", "Club name (partial match)"),
          "position" => @str,
          "min_overall" => @int,
          "max_age" => @int,
          "brazilian_clubs" => %{
            "type" => "boolean",
            "description" => "Only players at clubs that appear in the Brazilian match data"
          },
          "sort_by" => %{"type" => "string", "enum" => ["overall", "potential", "age", "name"]},
          "limit" => @limit
        }
      ),
      tool(
        "player_details",
        "Full FIFA profile of a player: club, position, ratings, physical data and best attributes.",
        %{"name" => @str},
        ["name"]
      ),
      tool(
        "brazilian_clubs_players",
        "Summary of FIFA players at Brazilian clubs: player count, average rating and best player per club. Optionally only players of one nationality.",
        %{"nationality" => @str}
      ),
      tool(
        "list_teams",
        "List known teams (canonical name, state, number of matches); use to check spelling.",
        %{"query" => @str, "limit" => @limit}
      ),
      tool(
        "dataset_info",
        "Describe the loaded datasets: files, row counts, competitions and season coverage.",
        %{}
      )
    ]
  end

  defp tool(name, description, properties, required \\ []) do
    %{
      "name" => name,
      "description" => description,
      "inputSchema" => %{"type" => "object", "properties" => properties, "required" => required}
    }
  end

  def names, do: Enum.map(list(), & &1["name"])

  @doc "Runs a tool. `args` is the JSON arguments map (string keys)."
  def call(name, args, data \\ nil) do
    if name in names() do
      data = data || Data.get()

      try do
        run(name, args || %{}, data)
      rescue
        e -> {:error, "Tool #{name} failed: #{Exception.message(e)}"}
      end
    else
      {:error, :unknown_tool}
    end
  end

  # ------------------------------------------------------------------ tools

  defp run("search_matches", a, d) do
    limit = limit(a, 20)

    with {:ok, ms} <-
           Queries.matches(
             d,
             filters(a, ~w(team opponent venue competition season date_from date_to round stage))
           ) do
      title = "Matches" <> describe(a, d) <> ": #{length(ms)} found"

      h2h =
        if a["team"] && a["opponent"] && ms != [] do
          {:ok, h} =
            Queries.head_to_head(
              d,
              a["team"],
              a["opponent"],
              filters(a, ~w(competition season date_from date_to))
            )

          "\n\n" <> Format.head_to_head(h)
        else
          ""
        end

      body =
        if ms == [],
          do: "No matches found in the dataset.",
          else: Format.match_list(ms, limit, &Format.match_detail/1)

      {:ok, title <> "\n" <> body <> h2h}
    end
  end

  defp run("head_to_head", a, d) do
    with {:ok, a1} <- required(a, "team_a"),
         {:ok, b1} <- required(a, "team_b"),
         {:ok, h} <-
           Queries.head_to_head(d, a1, b1, filters(a, ~w(competition season date_from date_to))) do
      if h.total == 0 do
        {:ok, "#{h.team_a} vs #{h.team_b}#{describe(a, d)}: no matches in the dataset."}
      else
        home_a = Queries.record(Enum.filter(h.matches, &(&1.home == h.key_a)), h.key_a)
        home_b = Queries.record(Enum.filter(h.matches, &(&1.home == h.key_b)), h.key_b)

        {:ok,
         """
         #{h.team_a} vs #{h.team_b}#{describe(a, d)}:
         #{Format.match_list(h.matches, limit(a, 10))}

         #{Format.head_to_head(h)}
         - #{h.team_a} at home: #{Format.record_line(home_a)}
         - #{h.team_b} at home: #{Format.record_line(home_b)}\
         """}
      end
    end
  end

  defp run("team_stats", a, d) do
    with {:ok, team} <- required(a, "team"),
         {:ok, s} <-
           Queries.team_stats(d, team, filters(a, ~w(venue competition season date_from date_to))) do
      venue = if a["venue"] in ["home", "away"], do: " #{a["venue"]}", else: ""

      head =
        "#{s.team}#{venue} record#{describe(Map.drop(a, ["team", "venue"]), d)}:\n#{Format.record(s.overall)}"

      splits =
        if venue == "" and s.overall.matches > 0,
          do: "\n\nHome: #{Format.record_line(s.home)}\nAway: #{Format.record_line(s.away)}",
          else: ""

      comps =
        if length(s.by_competition) > 1,
          do:
            "\n\nBy competition:\n" <>
              Enum.map_join(s.by_competition, "\n", fn {c, r} ->
                "- #{c}: #{Format.record_line(r)}"
              end),
          else: ""

      {:ok, head <> splits <> comps}
    end
  end

  defp run("team_profile", a, d) do
    with {:ok, team} <- required(a, "team"),
         {:ok, p} <- Queries.team_profile(d, team) do
      comps =
        Enum.map_join(p.competitions, "\n", fn {c, seasons, r} ->
          "- #{c} (#{span(seasons)}): #{Format.record_line(r)}"
        end)

      squad =
        case p.squad do
          [] ->
            "No players for this club in the FIFA dataset."

          list ->
            "FIFA dataset squad (#{length(list)} players, top 10 by rating):\n" <>
              Format.numbered(Enum.take(list, 10), &Format.player/1)
        end

      {:ok,
       """
       #{p.team}#{if p.state, do: " (#{p.state})", else: ""} - profile across all datasets
       Overall: #{Format.record_line(p.overall)}

       Competitions played:
       #{comps}

       Most recent matches:
       #{Format.match_list(p.matches, 5)}

       #{squad}\
       """}
    end
  end

  defp run("standings", a, d) do
    with {:ok, s} <- Queries.standings(d, a["competition"] || "Brasileirão Série A", a["season"]) do
      rows = Enum.take(s.rows, limit(a, 100))
      {:ok, Format.standings(%{s | rows: rows})}
    end
  end

  defp run("knockout_bracket", a, d) do
    with {:ok, comp} <- required(a, "competition"),
         {:ok, b} <- Queries.bracket(d, comp, a["season"]) do
      if b.rounds == [] do
        {:ok, "No #{b.competition} matches for season #{a["season"]} in the dataset."}
      else
        rounds =
          Enum.map_join(b.rounds, "\n\n", fn {label, ms} ->
            "#{String.capitalize(label)} (#{length(ms)} matches):\n" <>
              Enum.map_join(
                ms,
                "\n",
                &"- #{&1.date}: #{&1.home_name} #{&1.home_goals}-#{&1.away_goals} #{&1.away_name}"
              )
          end)

        has_final = Enum.any?(b.rounds, fn {_, ms} -> Enum.any?(ms, &(&1.stage == "final")) end)

        champ =
          cond do
            b.champion ->
              "\n\nChampion (final won on aggregate): #{b.champion}"

            has_final ->
              "\n\nThe final was level on aggregate; the tie-breaker (penalties/away goals) is not in the data."

            true ->
              "\n\nThe final of this season is not in the dataset."
          end

        {:ok, "#{b.season} #{b.competition}:\n\n" <> rounds <> champ}
      end
    end
  end

  defp run("team_rankings", a, d) do
    opts = filters(a, ~w(competition season date_from date_to venue metric order min_matches))

    with {:ok, r} <- Queries.rankings(d, opts) do
      venue = %{home: "home ", away: "away ", any: ""}[r.venue]

      rows =
        Format.numbered(Enum.take(r.rows, limit(a, 10)), fn t ->
          "#{t.team} - #{r.metric}: #{Map.fetch!(t, r.metric)} (#{venue}#{Format.record_line(t)})"
        end)

      {:ok,
       "Team ranking by #{venue}#{r.metric}#{describe(a, d)} (#{r.matches} matches, teams with at least #{r.min_matches} #{venue}matches):\n" <>
         if(rows == "", do: "No teams match.", else: rows)}
    end
  end

  defp run("biggest_wins", a, d) do
    with {:ok, ms} <-
           Queries.biggest_wins(
             d,
             filters(a, ~w(team competition season date_from date_to)),
             limit(a, 10)
           ) do
      {:ok,
       "Biggest victories#{describe(a, d)}:\n" <>
         if(ms == [], do: "No matches found.", else: Format.numbered(ms, &Format.match/1))}
    end
  end

  defp run("competition_stats", a, d) do
    f = filters(a, ~w(team competition season date_from date_to))

    case a["seasons"] do
      list when is_list(list) and list != [] ->
        results =
          Enum.map(list, fn season ->
            with {:ok, s} <- Queries.summary(d, Map.put(f, :season, season)) do
              champ =
                case a["team"] == nil &&
                       Queries.standings(d, a["competition"] || "Brasileirão Série A", season) do
                  {:ok, %{complete: true, rows: [first | _]}} ->
                    "\n- Champion: #{first.team} (#{first.points} pts)"

                  _ ->
                    ""
                end

              {:ok, "Season #{season}:\n#{Format.summary(s)}#{champ}"}
            end
          end)

        case Enum.find(results, &match?({:error, _}, &1)) do
          nil ->
            {:ok,
             "Season comparison#{describe(Map.delete(a, "season"), d)}:\n\n" <>
               Enum.map_join(results, "\n\n", &elem(&1, 1))}

          err ->
            err
        end

      _ ->
        with {:ok, s} <- Queries.summary(d, f) do
          {:ok, "Statistics#{describe(a, d)}:\n" <> Format.summary(s)}
        end
    end
  end

  defp run("derbies", a, d) do
    with {:ok, list} <-
           Queries.derbies(d, filters(a, ~w(team competition season date_from date_to))) do
      shown = Enum.take(list, limit(a, 30))
      more = length(list) - length(shown)
      lines = Enum.map(shown, fn {nick, m} -> "- #{Format.match(m)} [#{nick}]" end)
      lines = if more > 0, do: lines ++ ["- ... (#{more} more matches in dataset)"], else: lines
      {:ok, "Derbies#{describe(a, d)}: #{length(list)} found\n" <> Enum.join(lines, "\n")}
    end
  end

  defp run("search_players", a, d) do
    {:ok, ps} =
      Queries.players(
        d,
        filters(a, ~w(name nationality club position min_overall max_age brazilian_clubs sort_by))
      )

    shown = Enum.take(ps, limit(a, 20))

    note =
      cond do
        ps == [] and a["club"] ->
          "\nNo players found. Note: the FIFA dataset only licenses some Brazilian clubs (use brazilian_clubs_players to see which)."

        ps == [] ->
          "\nNo players found."

        length(ps) > length(shown) ->
          "\n... (#{length(ps) - length(shown)} more players in dataset)"

        true ->
          ""
      end

    {:ok,
     "Players#{describe_players(a)}: #{length(ps)} found\n" <>
       Format.numbered(shown, &Format.player/1) <> note}
  end

  defp run("player_details", a, d) do
    with {:ok, name} <- required(a, "name") do
      {:ok, ps} = Queries.players(d, name: name)

      case ps do
        [] ->
          {:ok, "No player matching #{inspect(name)} in the FIFA dataset."}

        list ->
          exact = Enum.filter(list, &(Text.normalize(&1.name) == Text.normalize(name)))
          shown = Enum.take(if(exact == [], do: list, else: exact), 3)
          more = length(list) - length(shown)

          {:ok,
           Enum.map_join(shown, "\n\n", &Format.player_detail/1) <>
             if(more > 0,
               do:
                 "\n\n(#{more} other players also match #{inspect(name)}; use search_players to list them)",
               else: ""
             )}
      end
    end
  end

  defp run("brazilian_clubs_players", a, d) do
    rows = Queries.brazilian_club_summary(d, filters(a, ~w(nationality)))
    who = if a["nationality"], do: "#{a["nationality"]} players", else: "Players"

    {:ok,
     "#{who} at Brazilian clubs in the FIFA dataset (#{Enum.sum(Enum.map(rows, & &1.players))} players, #{length(rows)} clubs):\n" <>
       Enum.map_join(rows, "\n", fn r ->
         "- #{r.club}: #{r.players} players (avg rating: #{r.avg_overall}; best: #{r.best.name}, #{r.best.overall})"
       end)}
  end

  defp run("list_teams", a, d) do
    teams = Queries.teams(d, a["query"])
    shown = Enum.take(teams, limit(a, 50))

    {:ok,
     "Teams: #{length(teams)} found\n" <>
       Enum.map_join(shown, "\n", fn t ->
         "- #{t.name}#{if t.state, do: " (#{t.state})", else: ""}: #{t.matches} matches"
       end) <>
       if(length(teams) > length(shown),
         do: "\n... (#{length(teams) - length(shown)} more)",
         else: ""
       )}
  end

  defp run("dataset_info", _a, d) do
    files =
      for src <- [:brasileirao, :cup, :libertadores, :br_football, :historical] do
        f = d.files[src]
        "- #{f.file}: #{f.rows} rows (#{f.played} played matches with a result)"
      end

    comps =
      d.matches
      |> Enum.group_by(& &1.competition)
      |> Enum.sort()
      |> Enum.map(fn {c, ms} ->
        "- #{c}: #{length(ms)} matches, seasons #{ms |> Enum.map(& &1.season) |> Enum.uniq() |> Enum.sort() |> span()}"
      end)

    {:ok,
     """
     Brazilian soccer knowledge base
     Match files:
     #{Enum.join(files, "\n")}
     - #{d.files.merged_duplicates} rows describing a match already present in another file were merged
     Unique matches: #{length(d.matches)} between #{map_size(d.teams)} teams (#{List.last(d.matches).date} to #{hd(d.matches).date})
     #{Enum.join(comps, "\n")}
     Players: #{length(d.players)} from #{d.files.fifa.file} (#{Enum.count(d.players, &(&1.nationality == "Brazil"))} Brazilian)\
     """}
  end

  # ---------------------------------------------------------------- helpers

  defp filters(args, keys) do
    for k <- keys, v = args[k], v not in [nil, ""], into: %{}, do: {String.to_atom(k), v}
  end

  defp required(args, key) do
    case args[key] do
      v when is_binary(v) and v != "" -> {:ok, v}
      _ -> {:error, "Missing required argument: #{key}"}
    end
  end

  defp limit(args, default) do
    case Text.to_int(args["limit"]) do
      n when is_integer(n) and n > 0 -> min(n, 500)
      _ -> default
    end
  end

  defp span([]), do: "none"
  defp span([s]), do: "#{s}"
  defp span(seasons), do: "#{List.first(seasons)}-#{List.last(seasons)}"

  # Human-readable summary of the filters, using canonical names.
  defp describe(a, d) do
    team = fn name ->
      case name && Queries.resolve_team(d, name) do
        {:ok, k} -> Queries.team_name(d, k)
        _ -> name
      end
    end

    comp =
      case a["competition"] && Queries.resolve_competition(a["competition"]) do
        {:ok, c} -> c
        _ -> nil
      end

    parts =
      [
        cond do
          a["team"] && a["opponent"] -> "#{team.(a["team"])} vs #{team.(a["opponent"])}"
          a["team"] -> team.(a["team"])
          true -> nil
        end,
        a["venue"] in ["home", "away"] && a["team"] && a["venue"],
        comp,
        a["season"] && "#{a["season"]}",
        a["stage"] && "stage #{a["stage"]}",
        a["round"] && "round #{a["round"]}",
        a["date_from"] && "from #{a["date_from"]}",
        a["date_to"] && "until #{a["date_to"]}"
      ]
      |> Enum.filter(& &1)

    if parts == [],
      do: " (all competitions in dataset)",
      else: " (" <> Enum.join(parts, ", ") <> ")"
  end

  defp describe_players(a) do
    parts =
      for k <- ~w(name nationality club position min_overall max_age),
          v = a[k],
          v not in [nil, ""],
          do: "#{k}: #{v}"

    parts = if a["brazilian_clubs"] == true, do: parts ++ ["at Brazilian clubs"], else: parts
    if parts == [], do: "", else: " (" <> Enum.join(parts, ", ") <> ")"
  end
end
