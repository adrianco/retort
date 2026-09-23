defmodule BrSoccer.Tools do
  @moduledoc "MCP tool definitions and their text-formatted implementations."

  alias BrSoccer.{Data, Query, Team}

  @str %{"type" => "string"}
  @int %{"type" => "integer"}

  defp schema(props, required \\ []),
    do: %{"type" => "object", "properties" => props, "required" => required}

  @comp Map.put(@str, "description", "brasileirao / serie_a, serie_b, serie_c, copa_do_brasil, libertadores")

  def definitions do
    [
      %{
        "name" => "search_matches",
        "description" =>
          "Find matches by team, opponent, venue, season, competition, date range (YYYY-MM-DD or DD/MM/YYYY) or stage (e.g. 'final').",
        "inputSchema" =>
          schema(%{
            "team" => @str,
            "opponent" => @str,
            "venue" => Map.put(@str, "enum", ["home", "away", "any"]),
            "season" => @int,
            "competition" => @comp,
            "date_from" => @str,
            "date_to" => @str,
            "stage" => @str,
            "limit" => @int
          })
      },
      %{
        "name" => "head_to_head",
        "description" => "Head-to-head record and recent matches between two teams.",
        "inputSchema" =>
          schema(%{"team_a" => @str, "team_b" => @str, "competition" => @comp, "season" => @int, "limit" => @int}, [
            "team_a",
            "team_b"
          ])
      },
      %{
        "name" => "team_stats",
        "description" => "Win/draw/loss record, goals for/against and win rate for a team, optionally by season, competition and venue.",
        "inputSchema" =>
          schema(
            %{
              "team" => @str,
              "season" => @int,
              "competition" => @comp,
              "venue" => Map.put(@str, "enum", ["home", "away", "any"])
            },
            ["team"]
          )
      },
      %{
        "name" => "team_competitions",
        "description" => "Which competitions and seasons a team appears in across all match files.",
        "inputSchema" => schema(%{"team" => @str}, ["team"])
      },
      %{
        "name" => "standings",
        "description" => "League table for a season calculated from match results (champion, relegation zone).",
        "inputSchema" => schema(%{"season" => @int, "competition" => @comp, "limit" => @int}, ["season"])
      },
      %{
        "name" => "cup_finals",
        "description" => "Final matches of Copa do Brasil (last round each season) or Copa Libertadores.",
        "inputSchema" => schema(%{"competition" => @comp, "season" => @int})
      },
      %{
        "name" => "competition_stats",
        "description" => "Average goals per match and home/away/draw rates for a competition and/or season.",
        "inputSchema" => schema(%{"competition" => @comp, "season" => @int, "team" => @str})
      },
      %{
        "name" => "biggest_wins",
        "description" => "Largest victory margins in the data.",
        "inputSchema" => schema(%{"competition" => @comp, "season" => @int, "team" => @str, "limit" => @int})
      },
      %{
        "name" => "best_records",
        "description" => "Rank teams by win rate (home, away or overall) — e.g. 'which team has the best away record?'.",
        "inputSchema" =>
          schema(%{
            "venue" => Map.put(@str, "enum", ["home", "away", "any"]),
            "competition" => @comp,
            "season" => @int,
            "min_matches" => @int,
            "limit" => @int
          })
      },
      %{
        "name" => "top_scoring_teams",
        "description" => "Teams ranked by goals scored in a league season.",
        "inputSchema" => schema(%{"season" => @int, "competition" => @comp, "limit" => @int}, ["season"])
      },
      %{
        "name" => "derbies",
        "description" => "Matches between traditional rivals (Fla-Flu, Grenal, Derby Paulista, ...).",
        "inputSchema" => schema(%{"season" => @int, "competition" => @comp, "limit" => @int})
      },
      %{
        "name" => "compare_seasons",
        "description" => "Compare aggregate statistics and champions of two league seasons.",
        "inputSchema" => schema(%{"season_a" => @int, "season_b" => @int, "competition" => @comp}, ["season_a", "season_b"])
      },
      %{
        "name" => "search_players",
        "description" => "Search FIFA player database by name, nationality, club, position (e.g. ST or 'forward') and min rating.",
        "inputSchema" =>
          schema(%{
            "name" => @str,
            "nationality" => @str,
            "club" => @str,
            "position" => @str,
            "min_overall" => @int,
            "limit" => @int
          })
      },
      %{
        "name" => "club_profile",
        "description" => "Cross-dataset club overview: match record across all competitions plus FIFA squad (top-rated players).",
        "inputSchema" => schema(%{"team" => @str, "season" => @int, "limit" => @int}, ["team"])
      },
      %{
        "name" => "players_by_club",
        "description" => "Count and average rating of players (optionally of one nationality) grouped by club.",
        "inputSchema" => schema(%{"nationality" => @str, "limit" => @int})
      }
    ]
  end

  @doc "Runs a tool. Returns {:ok, text} or {:error, message}."
  def call(name, args) when is_map(args) do
    opts = for {k, v} <- args, v not in [nil, ""], key = known_key(k), key != nil, do: {key, to_s(v)}
    run(name, opts)
  rescue
    e -> {:error, "Error running #{name}: #{Exception.message(e)}"}
  end

  # Only accept argument names that already exist as atoms (no atom leaks).
  defp known_key(k) do
    String.to_existing_atom(k)
  rescue
    ArgumentError -> nil
  end

  defp to_s(v) when is_binary(v), do: v
  defp to_s(v), do: to_string(v)

  defp limit(opts, default), do: Data.parse_int(opts[:limit]) || default

  defp run("search_matches", opts) do
    with :ok <- check_comp(opts) do
      ms = Query.matches(opts)
      n = limit(opts, 20)
      title = "Found #{length(ms)} matches" <> if(length(ms) > n, do: " (showing #{n})", else: "")
      more = if length(ms) > n, do: ["- ... (#{length(ms) - n} more matches in dataset)"], else: []
      {:ok, lines([title <> ":" | Enum.map(Enum.take(ms, n), &("- " <> fmt_match(&1)))] ++ more)}
    end
  end

  defp run("head_to_head", opts) do
    with :ok <- check_comp(opts) do
      a = opts[:team_a]
      b = opts[:team_b]
      h = Query.head_to_head(a, b, Keyword.take(opts, [:competition, :season]))
      ka = Team.canonical(a)
      kb = Team.canonical(b)
      derby = Team.derby(ka, kb)
      n = limit(opts, 10)
      head = "#{Team.display(ka)} vs #{Team.display(kb)}" <> if(derby, do: " (#{derby})", else: "") <> ":"
      shown = h.matches |> Enum.take(n) |> Enum.map(&("- " <> fmt_match(&1)))
      rest = length(h.matches) - length(shown)
      more = if rest > 0, do: ["- ... (#{rest} more matches in dataset)"], else: []

      {:ok,
       lines(
         [head | shown] ++
           more ++
           [
             "",
             "Head-to-head in dataset (#{length(h.matches)} matches): #{Team.display(ka)} #{h.a_wins} wins, " <>
               "#{Team.display(kb)} #{h.b_wins} wins, #{h.draws} draws",
             "Goals: #{Team.display(ka)} #{h.a_goals} - #{h.b_goals} #{Team.display(kb)}"
           ]
       )}
    end
  end

  defp run("team_stats", opts) do
    with :ok <- check_comp(opts) do
      t = opts[:team]
      r = Query.team_record(t, opts)
      venue = if opts[:venue] in ["home", "away"], do: "#{opts[:venue]} ", else: ""
      scope = [opts[:season], comp_label(opts)] |> Enum.reject(&is_nil/1) |> Enum.join(" ")
      scope = if scope == "", do: "all competitions", else: scope

      by_comp =
        r.by_competition
        |> Enum.sort_by(fn {_, n} -> -n end)
        |> Enum.map(fn {c, n} -> "  - #{Data.competition_name(c)}: #{n}" end)

      {:ok,
       lines(
         [
           "#{Team.display(Team.canonical(t))} #{venue}record (#{scope}):",
           "- Matches: #{r.played}",
           "- Wins: #{r.wins}, Draws: #{r.draws}, Losses: #{r.losses}",
           "- Goals For: #{r.gf}, Goals Against: #{r.ga}",
           "- Win rate: #{Query.win_rate(r)}%",
           "- Matches by competition:"
         ] ++ by_comp
       )}
    end
  end

  defp run("team_competitions", opts) do
    t = opts[:team]

    rows =
      for {c, n, seasons} <- Query.team_competitions(t),
          do: "- #{Data.competition_name(c)}: #{n} matches (seasons #{Enum.join(seasons, ", ")})"

    {:ok, lines(["Competitions for #{Team.display(Team.canonical(t))}:" | none(rows)])}
  end

  defp run("standings", opts) do
    opts = Keyword.put_new(opts, :competition, "serie_a")

    with :ok <- check_comp(opts) do
      table = Query.standings(opts[:season], opts[:competition])
      size = length(table)
      n = limit(opts, size)

      rows =
        table
        |> Enum.with_index(1)
        |> Enum.take(n)
        |> Enum.map(fn {r, i} ->
          tag =
            cond do
              i == 1 -> " - Champion"
              size >= 16 and i > size - 4 -> " - Relegated"
              true -> ""
            end

          "#{i}. #{Team.display(r.team)} - #{r.points} pts (#{r.wins}W, #{r.draws}D, #{r.losses}L, GF #{r.gf}, GA #{r.ga}, GD #{r.gd})#{tag}"
        end)

      {:ok, lines(["#{opts[:season]} #{comp_label(opts)} Final Standings (calculated from matches):" | none(rows)])}
    end
  end

  defp run("cup_finals", opts) do
    opts = Keyword.put_new(opts, :competition, "copa_do_brasil")

    with :ok <- check_comp(opts) do
      ms = finals(opts)
      {:ok, lines(["#{comp_label(opts)} finals in dataset:" | none(Enum.map(ms, &("- " <> fmt_match(&1))))])}
    end
  end

  defp run("competition_stats", opts) do
    with :ok <- check_comp(opts) do
      s = Query.summary(opts)
      scope = [comp_label(opts) || "All competitions", opts[:season], opts[:team]] |> Enum.reject(&is_nil/1) |> Enum.join(" ")

      {:ok,
       lines([
         "Statistics (#{scope}):",
         "- Matches: #{s.matches}",
         "- Total goals: #{s.goals}",
         "- Average goals per match: #{s.avg_goals}",
         "- Home win rate: #{s.home_win_pct}%",
         "- Away win rate: #{s.away_win_pct}%",
         "- Draw rate: #{s.draw_pct}%"
       ])}
    end
  end

  defp run("biggest_wins", opts) do
    with :ok <- check_comp(opts) do
      ms = Query.biggest_wins(opts)
      rows = ms |> Enum.with_index(1) |> Enum.map(fn {m, i} -> "#{i}. #{fmt_match(m)}" end)
      {:ok, lines(["Biggest victories (#{comp_label(opts) || "all competitions"}):" | none(rows)])}
    end
  end

  defp run("best_records", opts) do
    with :ok <- check_comp(opts) do
      venue = opts[:venue] || "any"
      rows = Query.best_records(opts) |> Enum.take(limit(opts, 10)) |> Enum.with_index(1)

      rows =
        for {r, i} <- rows,
            do: "#{i}. #{Team.display(r.team)} - #{Query.win_rate(r)}% wins (#{r.wins}W #{r.draws}D #{r.losses}L in #{r.played}, GF #{r.gf} GA #{r.ga})"

      label = if venue == "any", do: "overall", else: venue
      {:ok, lines(["Best #{label} records (#{comp_label(opts) || "all competitions"}):" | none(rows)])}
    end
  end

  defp run("top_scoring_teams", opts) do
    opts = Keyword.put_new(opts, :competition, "serie_a")

    with :ok <- check_comp(opts) do
      rows =
        Query.top_scoring_teams(opts)
        |> Enum.take(limit(opts, 10))
        |> Enum.with_index(1)
        |> Enum.map(fn {r, i} -> "#{i}. #{Team.display(r.team)} - #{r.gf} goals scored (#{r.played} matches)" end)

      {:ok, lines(["Top scoring teams #{opts[:season]} #{comp_label(opts)}:" | none(rows)])}
    end
  end

  defp run("derbies", opts) do
    with :ok <- check_comp(opts) do
      ms = Query.derbies(opts)
      n = limit(opts, 30)
      rows = ms |> Enum.take(n) |> Enum.map(&"- [#{&1.derby}] #{fmt_match(&1)}")
      {:ok, lines(["Derbies found: #{length(ms)}" | rows])}
    end
  end

  defp run("compare_seasons", opts) do
    opts = Keyword.put_new(opts, :competition, "serie_a")

    with :ok <- check_comp(opts) do
      rows =
        for season <- [opts[:season_a], opts[:season_b]] do
          s = Query.summary(season: season, competition: opts[:competition])
          table = Query.standings(season, opts[:competition])
          champ = List.first(table)
          top = Enum.max_by(table, & &1.gf, fn -> nil end)

          [
            "#{season} #{comp_label(opts)}:",
            "- Matches: #{s.matches}, Goals: #{s.goals}, Avg goals/match: #{s.avg_goals}",
            "- Home wins: #{s.home_win_pct}%, Away wins: #{s.away_win_pct}%, Draws: #{s.draw_pct}%",
            "- Champion: #{if champ, do: "#{Team.display(champ.team)} (#{champ.points} pts)", else: "n/a"}",
            "- Most goals: #{if top, do: "#{Team.display(top.team)} (#{top.gf})", else: "n/a"}"
          ]
        end

      {:ok, rows |> Enum.intersperse([""]) |> List.flatten() |> lines()}
    end
  end

  defp run("search_players", opts) do
    ps = Query.players(Keyword.delete(opts, :limit))
    n = limit(opts, 25)

    rows =
      ps
      |> Enum.take(n)
      |> Enum.with_index(1)
      |> Enum.map(fn {p, i} ->
        "#{i}. #{p.name} - Overall: #{p.overall}, Potential: #{p.potential}, Position: #{p.position || "-"}, " <>
          "Club: #{p.club || "Free agent"}, Nationality: #{p.nationality}, Age: #{p.age}" <>
          if(length(ps) <= 3, do: player_details(p), else: "")
      end)

    {:ok, lines(["Found #{length(ps)} players" <> if(length(ps) > n, do: " (showing top #{n})", else: "") <> ":" | rows])}
  end

  defp run("players_by_club", opts) do
    rows =
      Query.players_by_club(Keyword.delete(opts, :limit))
      |> Enum.take(limit(opts, 20))
      |> Enum.map(fn {c, n, avg} -> "- #{c}: #{n} players (avg rating: #{avg})" end)

    {:ok, lines(["Players by club#{if opts[:nationality], do: " (#{opts[:nationality]})"}:" | none(rows)])}
  end

  defp run("club_profile", opts) do
    t = opts[:team]
    {:ok, record} = run("team_stats", Keyword.take(opts, [:team, :season]))
    {:ok, comps} = run("team_competitions", team: t)
    squad = Query.players(club: t, limit: limit(opts, 10))

    rows =
      for p <- squad, do: "- #{p.name} (#{p.position}) - Overall #{p.overall}, #{p.nationality}"

    {:ok, lines([record, "", comps, "", "FIFA squad (top-rated):" | none(rows)])}
  end

  defp run(name, _), do: {:error, "Unknown tool: #{name}"}

  # ---------------------------------------------------------------- helpers

  defp finals(opts) do
    case Data.parse_competition(opts[:competition]) do
      :libertadores ->
        Query.matches(Keyword.put(opts, :stage, "final"))

      _ ->
        Query.matches(opts)
        |> Enum.group_by(& &1.season)
        |> Enum.flat_map(fn {_, ms} ->
          # Seasons whose last recorded round is early are incomplete in the data.
          max = ms |> Enum.map(&(&1.round || 0)) |> Enum.max()
          Enum.filter(ms, &(&1.round == max and max >= 6 and is_integer(&1.home_goal)))
        end)
        |> Enum.sort_by(& &1.date, {:desc, Date})
    end
  end

  defp check_comp(opts) do
    if Data.parse_competition(opts[:competition]) == :unknown,
      do: {:error, "Unknown competition '#{opts[:competition]}'. Use serie_a, serie_b, serie_c, copa_do_brasil or libertadores."},
      else: :ok
  end

  defp comp_label(opts) do
    case Data.parse_competition(opts[:competition]) do
      nil -> nil
      :unknown -> nil
      c -> Data.competition_name(c)
    end
  end

  def fmt_match(m) do
    extra =
      cond do
        m.round && m.competition == :serie_a -> " Round #{m.round}"
        m.round -> " round #{m.round}"
        m.stage -> " #{m.stage}"
        true -> ""
      end

    "#{Date.to_iso8601(m.date)}: #{m.home} #{m.home_goal}-#{m.away_goal} #{m.away} (#{Data.competition_name(m.competition)}#{extra})"
  end

  defp player_details(p) do
    skills = p.skills |> Enum.reject(fn {_, v} -> is_nil(v) end) |> Enum.map_join(", ", fn {k, v} -> "#{k} #{v}" end)

    "\n   Height: #{p.height}, Weight: #{p.weight}, Foot: #{p.foot}, Jersey: #{p.jersey}, Value: #{p.value}, Wage: #{p.wage}" <>
      "\n   Skills: #{skills}"
  end

  defp none([]), do: ["(no results)"]
  defp none(rows), do: rows

  defp lines(list), do: Enum.join(list, "\n")
end
