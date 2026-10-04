defmodule BrazilianSoccer.MCP.Tools do
  @moduledoc """
  MCP tool definitions and their implementations. Every tool takes a map of
  string-keyed arguments and returns `{:ok, text}` or `{:error, message}`.
  """

  alias BrazilianSoccer.{Match, Players, Queries, Store, Text}

  @team %{
    "type" => "string",
    "description" =>
      "Team name; any common spelling works (\"Palmeiras\", \"Palmeiras-SP\", \"Atlético-MG\", \"Sao Paulo\")."
  }
  @competition %{
    "type" => "string",
    "description" =>
      "Competition: \"Brasileirão\" / \"Serie A\", \"Serie B\", \"Serie C\", \"Copa do Brasil\" or \"Libertadores\". Omit for all."
  }
  @season %{"type" => "integer", "description" => "Season year, e.g. 2019."}
  @venue %{
    "type" => "string",
    "enum" => ["home", "away", "either"],
    "description" => "Restrict to the team's home or away matches (default either)."
  }
  @limit %{"type" => "integer", "description" => "Maximum number of rows to list."}

  @tools [
    %{
      "name" => "search_matches",
      "description" =>
        "Find matches by team, opponent, competition, season, date range, round or stage (e.g. stage \"final\" for Copa do Brasil / Libertadores finals). Returns matches newest first, plus a head-to-head summary when both team and opponent are given.",
      "inputSchema" => %{
        "type" => "object",
        "properties" => %{
          "team" => @team,
          "opponent" => Map.put(@team, "description", "Opposing team name."),
          "venue" => @venue,
          "competition" => @competition,
          "season" => @season,
          "date_from" => %{
            "type" => "string",
            "description" => "Earliest date (YYYY-MM-DD or DD/MM/YYYY)."
          },
          "date_to" => %{
            "type" => "string",
            "description" => "Latest date (YYYY-MM-DD or DD/MM/YYYY)."
          },
          "round" => %{"type" => "integer", "description" => "Round number."},
          "stage" => %{
            "type" => "string",
            "description" =>
              "Knockout stage: \"group stage\", \"round of 16\", \"quarterfinals\", \"semifinals\", \"final\"."
          },
          "limit" => @limit
        }
      }
    },
    %{
      "name" => "head_to_head",
      "description" =>
        "Compare two teams head-to-head: wins, draws, goals and the list of their meetings (most recent first).",
      "inputSchema" => %{
        "type" => "object",
        "properties" => %{
          "team_a" => @team,
          "team_b" => @team,
          "competition" => @competition,
          "season" => @season,
          "limit" => @limit
        },
        "required" => ["team_a", "team_b"]
      }
    },
    %{
      "name" => "team_stats",
      "description" =>
        "Win/draw/loss record, goals for/against and win rate of a team — overall, home, away and per competition. Optionally restricted by season, competition and venue.",
      "inputSchema" => %{
        "type" => "object",
        "properties" => %{
          "team" => @team,
          "season" => @season,
          "competition" => @competition,
          "venue" => @venue
        },
        "required" => ["team"]
      }
    },
    %{
      "name" => "team_profile",
      "description" =>
        "Cross-dataset profile of a team: competitions and seasons played, overall record, most recent results and its squad in the FIFA player database.",
      "inputSchema" => %{
        "type" => "object",
        "properties" => %{"team" => @team},
        "required" => ["team"]
      }
    },
    %{
      "name" => "standings",
      "description" =>
        "League table for a season calculated from match results (3 points per win), marking the champion and relegated teams. Use it to answer who won a season or who was relegated.",
      "inputSchema" => %{
        "type" => "object",
        "properties" => %{"season" => @season, "competition" => @competition},
        "required" => ["season"]
      }
    },
    %{
      "name" => "team_rankings",
      "description" =>
        "Rank teams by win rate, points, points per match, wins, goals scored, goals conceded or goal difference — e.g. best home record, best away record, most goals in a season.",
      "inputSchema" => %{
        "type" => "object",
        "properties" => %{
          "sort_by" => %{
            "type" => "string",
            "enum" => [
              "win_rate",
              "points",
              "points_per_match",
              "wins",
              "goals_for",
              "goals_against",
              "goal_difference"
            ],
            "description" => "Ranking metric (default win_rate)."
          },
          "venue" => @venue,
          "competition" => @competition,
          "season" => @season,
          "min_matches" => %{
            "type" => "integer",
            "description" => "Minimum matches to qualify (default 10)."
          },
          "limit" => @limit
        }
      }
    },
    %{
      "name" => "competition_stats",
      "description" =>
        "Aggregate statistics for a competition and/or season: matches, goals per match, home/away win and draw rates, average corners.",
      "inputSchema" => %{
        "type" => "object",
        "properties" => %{"competition" => @competition, "season" => @season, "team" => @team}
      }
    },
    %{
      "name" => "compare_seasons",
      "description" =>
        "Compare two seasons of a competition: goals per match, home win rate, top of the table, best attack and defence.",
      "inputSchema" => %{
        "type" => "object",
        "properties" => %{
          "season_a" => @season,
          "season_b" => @season,
          "competition" => @competition
        },
        "required" => ["season_a", "season_b"]
      }
    },
    %{
      "name" => "biggest_wins",
      "description" =>
        "Largest victories by goal margin (or, with by=\"total_goals\", the highest-scoring matches), optionally filtered by team, competition and season.",
      "inputSchema" => %{
        "type" => "object",
        "properties" => %{
          "team" => @team,
          "competition" => @competition,
          "season" => @season,
          "by" => %{"type" => "string", "enum" => ["margin", "total_goals"]},
          "limit" => @limit
        }
      }
    },
    %{
      "name" => "derbies",
      "description" =>
        "Matches between traditional rivals (Fla-Flu, Derby Paulista, Gre-Nal, Clássico Mineiro, ...), optionally filtered by season, competition or team.",
      "inputSchema" => %{
        "type" => "object",
        "properties" => %{
          "season" => @season,
          "competition" => @competition,
          "team" => @team,
          "limit" => @limit
        }
      }
    },
    %{
      "name" => "search_players",
      "description" =>
        "Search the FIFA player database by name, nationality, club and position (a code like \"ST\" or a group: forwards, midfielders, defenders, goalkeepers). Sorted by overall rating by default.",
      "inputSchema" => %{
        "type" => "object",
        "properties" => %{
          "name" => %{
            "type" => "string",
            "description" => "Full or partial player name (accents optional)."
          },
          "nationality" => %{"type" => "string", "description" => "Country, e.g. \"Brazil\"."},
          "club" => %{
            "type" => "string",
            "description" => "Club name, e.g. \"Santos\", \"Grêmio\"."
          },
          "position" => %{"type" => "string", "description" => "Position code or group."},
          "min_overall" => %{"type" => "integer", "description" => "Minimum overall rating."},
          "max_age" => %{"type" => "integer", "description" => "Maximum age."},
          "sort_by" => %{"type" => "string", "enum" => ["overall", "potential", "age", "name"]},
          "limit" => @limit
        }
      }
    },
    %{
      "name" => "player_details",
      "description" =>
        "Full profile of a player: age, nationality, club, position, ratings, physical attributes and skill ratings.",
      "inputSchema" => %{
        "type" => "object",
        "properties" => %{"name" => %{"type" => "string", "description" => "Player name."}},
        "required" => ["name"]
      }
    },
    %{
      "name" => "players_by_club",
      "description" =>
        "Group players by club with counts and average rating — e.g. Brazilian players per club, or only at Brazilian clubs.",
      "inputSchema" => %{
        "type" => "object",
        "properties" => %{
          "nationality" => %{
            "type" => "string",
            "description" => "Country filter, e.g. \"Brazil\"."
          },
          "position" => %{"type" => "string", "description" => "Position code or group."},
          "brazilian_clubs_only" => %{
            "type" => "boolean",
            "description" => "Only clubs from the Brazilian leagues."
          },
          "limit" => @limit
        }
      }
    },
    %{
      "name" => "dataset_info",
      "description" =>
        "Describes the loaded datasets: files, row counts, competitions, season coverage.",
      "inputSchema" => %{"type" => "object", "properties" => %{}}
    }
  ]

  def list, do: @tools

  @doc "Dispatches a tool call."
  def call(name, args) when is_map(args) do
    if Enum.any?(@tools, &(&1["name"] == name)) do
      with :ok <- check_required(name, args) do
        run(name, args)
      end
    else
      {:error, "Unknown tool: #{name}"}
    end
  end

  def call(_name, _args), do: {:error, "Tool arguments must be an object"}

  defp check_required(name, args) do
    tool = Enum.find(@tools, &(&1["name"] == name))

    case Enum.filter(tool["inputSchema"]["required"] || [], &Text.blank?(to_str(args[&1]))) do
      [] -> :ok
      missing -> {:error, "Missing required argument(s): #{Enum.join(missing, ", ")}"}
    end
  end

  # ── tool implementations ───────────────────────────────────────────────

  defp run("search_matches", a) do
    filters = filters(a)
    ms = Queries.matches(filters)
    limit = limit(a, 20)

    header = "Matches#{describe(a)}: #{length(ms)} found"

    h2h =
      if filters[:team] && filters[:opponent] && ms != [] do
        h =
          Queries.head_to_head(
            filters.team,
            filters.opponent,
            Map.drop(filters, [:team, :opponent])
          )

        ["", h2h_line(h)]
      else
        []
      end

    {:ok, lines([header, match_lines(ms, limit), h2h])}
  end

  defp run("head_to_head", a) do
    filters = a |> Map.drop(["team_a", "team_b"]) |> filters()
    h = Queries.head_to_head(a["team_a"], a["team_b"], filters)

    if h.matches == [] do
      {:ok, "No matches found between #{h.team_a} and #{h.team_b}#{describe(a)}."}
    else
      ra = h.record_a
      title = "#{h.team_a} vs #{h.team_b}" <> if(h.derby, do: " (#{h.derby})", else: "")

      {:ok,
       lines([
         "#{title}#{describe(a)}: #{length(h.matches)} matches",
         match_lines(h.matches, limit(a, 15)),
         "",
         h2h_line(h),
         "Goals: #{h.team_a} #{ra.goals_for}, #{h.team_b} #{ra.goals_against}"
       ])}
    end
  end

  defp run("team_stats", a) do
    filters = filters(a)
    s = Queries.team_stats(a["team"], filters)

    if s.overall.matches == 0 do
      {:ok, "No played matches found for #{s.team}#{describe(a)}."}
    else
      sections =
        case filters[:venue] do
          "home" -> [{"Home record", s.home}]
          "away" -> [{"Away record", s.away}]
          _ -> [{"Overall", s.overall}, {"Home", s.home}, {"Away", s.away}]
        end

      by_comp =
        if length(s.by_competition) > 1 do
          ["", "By competition:"] ++
            for {c, r} <- s.by_competition, do: "- #{c}: #{short_record(r)}"
        else
          []
        end

      {:ok,
       lines([
         "#{s.team}#{describe(Map.delete(a, "team"))}:",
         Enum.map(sections, fn {title, r} -> record_block(title, r) end),
         by_comp
       ])}
    end
  end

  defp run("team_profile", a) do
    ref = Queries.team_ref(a["team"])
    comps = Queries.team_competitions(a["team"])
    ms = Queries.matches(%{team: a["team"]})
    squad = Players.search(%{club: a["team"]})

    if ms == [] and squad == [] do
      {:ok, "No data found for team \"#{a["team"]}\"."}
    else
      overall = Queries.record(ms, ref)

      {:ok,
       lines([
         "#{ref.name}" <> if(ref.state, do: " (#{ref.state})", else: ""),
         "",
         "Match data: #{short_record(overall)}",
         for(
           c <- comps,
           do: "- #{c.competition} (#{season_range(c.seasons)}): #{short_record(c.record)}"
         ),
         "",
         "Most recent matches:",
         match_lines(Enum.filter(ms, &Match.played?/1), 5),
         "",
         if(squad == [],
           do: "FIFA player data: no players listed for this club.",
           else: [
             "FIFA player data: #{length(squad)} players, average overall #{avg(squad)}",
             player_lines(squad, 10)
           ]
         )
       ])}
    end
  end

  defp run("standings", a) do
    st = Queries.standings(a["season"], a["competition"])

    cond do
      st.rows == [] ->
        {:ok, "No played matches found for #{st.competition} #{st.season}."}

      true ->
        title =
          if st.league,
            do:
              "#{st.season} #{st.competition} #{if st.complete, do: "Final Standings", else: "Standings (season incomplete in dataset)"} (calculated from matches):",
            else:
              "#{st.season} #{st.competition} — aggregate table of all matches (knockout competition, not an official ranking):"

        rows =
          for r <- st.rows do
            "#{r.position}. #{r.team} - #{r.points} pts (#{r.wins}W, #{r.draws}D, #{r.losses}L), GF #{r.goals_for}, GA #{r.goals_against}, GD #{signed(r.goal_difference)}" <>
              if(r.note, do: " - #{r.note}", else: "")
          end

        extra =
          if st.league do
            []
          else
            finals =
              Queries.matches(%{season: st.season, competition: st.competition, stage: "final"})

            if finals == [], do: [], else: ["", "Final:", match_lines(finals, 4)]
          end

        {:ok, lines([title, rows, extra])}
    end
  end

  defp run("team_rankings", a) do
    sort_by = a["sort_by"] || "win_rate"
    min = Text.parse_int(a["min_matches"]) || 10
    rows = Queries.rankings(filters(a), sort_by: sort_by, min_matches: min)
    venue = if a["venue"] in ["home", "away"], do: "#{a["venue"]} ", else: ""

    if rows == [] do
      {:ok, "No teams with at least #{min} #{venue}matches#{describe(a)}."}
    else
      {:ok,
       lines([
         "Teams ranked by #{venue}#{String.replace(sort_by, "_", " ")}#{describe(a)} (min #{min} matches):",
         rows
         |> Enum.take(limit(a, 10))
         |> Enum.with_index(1)
         |> Enum.map(fn {r, i} -> "#{i}. #{r.team} - #{short_record(r)}" end)
       ])}
    end
  end

  defp run("competition_stats", a) do
    s = Queries.summary(filters(a))

    if s.matches == 0 do
      {:ok, "No played matches found#{describe(a)}."}
    else
      {:ok,
       lines([
         "Statistics#{describe(a)}:",
         "- Matches: #{s.matches}",
         "- Goals: #{s.goals} (home #{s.home_goals}, away #{s.away_goals})",
         "- Average goals per match: #{fmt(s.goals_per_match, 2)}",
         "- Home wins: #{s.home_wins} (#{s.home_win_rate}%)",
         "- Draws: #{s.draws} (#{s.draw_rate}%)",
         "- Away wins: #{s.away_wins} (#{s.away_win_rate}%)",
         if(s.avg_corners,
           do: "- Average corners per match (where recorded): #{fmt(s.avg_corners, 2)}",
           else: []
         )
       ])}
    end
  end

  defp run("compare_seasons", a) do
    [x, y] = Queries.compare_seasons(a["season_a"], a["season_b"], a["competition"])

    block = fn s ->
      if s.summary.matches == 0 do
        ["#{s.season} #{s.competition}: no data", ""]
      else
        [
          "#{s.season} #{s.competition}#{if s.complete, do: "", else: " (incomplete in dataset)"}:",
          "- Matches: #{s.summary.matches}, goals: #{s.summary.goals} (#{fmt(s.summary.goals_per_match, 2)} per match)",
          "- Home wins #{s.summary.home_win_rate}%, draws #{s.summary.draw_rate}%, away wins #{s.summary.away_win_rate}%",
          "- Top 4: " <> Enum.map_join(s.top, ", ", &"#{&1.team} (#{&1.points} pts)"),
          "- Best attack: #{s.best_attack.team} (#{s.best_attack.goals_for} goals)",
          "- Best defence: #{s.best_defense.team} (#{s.best_defense.goals_against} conceded)",
          ""
        ]
      end
    end

    {:ok, lines([block.(x), block.(y)]) |> String.trim_trailing()}
  end

  defp run("biggest_wins", a) do
    limit = limit(a, 10)

    {title, ms} =
      if a["by"] == "total_goals",
        do: {"Highest-scoring matches", Queries.highest_scoring(filters(a), limit)},
        else: {"Biggest victories", Queries.biggest_wins(filters(a), limit)}

    if ms == [] do
      {:ok, "No played matches found#{describe(a)}."}
    else
      {:ok,
       lines([
         "#{title}#{describe(a)}:",
         ms |> Enum.with_index(1) |> Enum.map(fn {m, i} -> "#{i}. #{match_text(m)}" end)
       ])}
    end
  end

  defp run("derbies", a) do
    ds = Queries.derbies(filters(a))
    limit = limit(a, 30)

    if ds == [] do
      {:ok, "No derby matches found#{describe(a)}."}
    else
      shown = Enum.take(ds, limit)

      {:ok,
       lines([
         "Derby matches#{describe(a)}: #{length(ds)} found",
         for({name, m} <- shown, do: "- #{match_text(m)} [#{name}]"),
         more(length(ds) - length(shown))
       ])}
    end
  end

  defp run("search_players", a) do
    ps =
      Players.search(atomize(a, ~w(name nationality club position min_overall max_age sort_by)))

    if ps == [] do
      {:ok,
       "No players found#{player_desc(a)}. Note: the FIFA dataset does not include every Brazilian club (e.g. Flamengo, Corinthians, Palmeiras and São Paulo are missing)."}
    else
      {:ok,
       lines([
         "Players#{player_desc(a)}: #{length(ps)} found (average overall #{avg(ps)})",
         player_lines(ps, limit(a, 20))
       ])}
    end
  end

  defp run("player_details", a) do
    case Players.search(%{name: a["name"]}) do
      [] ->
        {:ok, "No player found matching \"#{a["name"]}\"."}

      [p | others] ->
        top = p.skills |> Enum.sort_by(&(-elem(&1, 1))) |> Enum.take(8)

        {:ok,
         lines([
           "#{p.name}",
           "- Age: #{p.age}",
           "- Nationality: #{p.nationality}",
           "- Club: #{p.club || "none"}",
           "- Position: #{p.position || "n/a"}, jersey number: #{p.jersey_number || "n/a"}",
           "- Overall: #{p.overall}, Potential: #{p.potential}",
           "- Height: #{p.height || "n/a"}, Weight: #{p.weight || "n/a"}, Preferred foot: #{p.preferred_foot || "n/a"}",
           "- Value: #{p.value || "n/a"}, Wage: #{p.wage || "n/a"}",
           "- Best attributes: " <> Enum.map_join(top, ", ", fn {k, v} -> "#{k} #{v}" end),
           if(others == [],
             do: [],
             else: ["", "Other matches for \"#{a["name"]}\":", player_lines(others, 5)]
           )
         ])}
    end
  end

  defp run("players_by_club", a) do
    opts =
      a
      |> atomize(~w(nationality position))
      |> Map.put(:brazilian_clubs_only, a["brazilian_clubs_only"] in [true, "true"])

    clubs = Players.by_club(opts)

    if clubs == [] do
      {:ok, "No players found#{player_desc(a)}."}
    else
      shown = Enum.take(clubs, limit(a, 25))

      {:ok,
       lines([
         "Players#{player_desc(a)} by club#{if opts.brazilian_clubs_only, do: " (Brazilian clubs only)", else: ""}: #{Enum.sum(Enum.map(clubs, & &1.players))} players at #{length(clubs)} clubs",
         for(
           c <- shown,
           do:
             "- #{c.club}: #{c.players} players (avg rating: #{c.avg_overall}; best: #{c.best.name}, #{c.best.overall})"
         ),
         more(length(clubs) - length(shown))
       ])}
    end
  end

  defp run("dataset_info", _a) do
    d = Store.data()

    comps =
      d.matches
      |> Enum.group_by(& &1.competition)
      |> Enum.sort_by(fn {_, ms} -> -length(ms) end)
      |> Enum.map(fn {c, ms} ->
        "- #{c}: #{length(ms)} matches, seasons #{ms |> Enum.map(& &1.season) |> Enum.uniq() |> Enum.sort() |> season_range()}"
      end)

    {:ok,
     lines([
       "Brazilian soccer datasets (data/kaggle):",
       d.file_counts |> Enum.sort() |> Enum.map(fn {f, n} -> "- #{f}: #{n} rows" end),
       "",
       "Unified match list: #{length(d.matches)} matches after merging fixtures that appear in several files",
       comps,
       "",
       "Players: #{length(d.players)} (FIFA database), #{Enum.count(d.players, &(&1.nationality == "Brazil"))} Brazilian"
     ])}
  end

  # ── formatting helpers ─────────────────────────────────────────────────

  defp filters(a) do
    atomize(a, ~w(team opponent venue competition season date_from date_to stage round))
  end

  defp atomize(a, keys) do
    for k <- keys, v = a[k], not Text.blank?(to_str(v)), into: %{} do
      {String.to_atom(k), if(is_binary(v), do: String.trim(v), else: v)}
    end
  end

  defp to_str(nil), do: nil
  defp to_str(v) when is_binary(v), do: v
  defp to_str(v), do: inspect(v)

  defp limit(a, default) do
    case Text.parse_int(a["limit"]) do
      n when is_integer(n) and n > 0 -> min(n, 500)
      _ -> default
    end
  end

  defp describe(a) do
    parts =
      [
        a["team"] && "team #{Queries.team_ref(a["team"]).name}",
        a["opponent"] && "opponent #{Queries.team_ref(a["opponent"]).name}",
        a["venue"] in ["home", "away"] && a["venue"],
        Queries.competition(a["competition"]),
        a["season"] && "season #{a["season"]}",
        a["stage"] && "stage #{a["stage"]}",
        a["round"] && "round #{a["round"]}",
        a["date_from"] && "from #{a["date_from"]}",
        a["date_to"] && "to #{a["date_to"]}"
      ]
      |> Enum.filter(& &1)

    if parts == [], do: " (all data)", else: " (" <> Enum.join(parts, ", ") <> ")"
  end

  defp player_desc(a) do
    parts =
      [
        a["name"] && "named \"#{a["name"]}\"",
        a["nationality"] && "nationality #{a["nationality"]}",
        a["club"] && "club #{a["club"]}",
        a["position"] && "position #{a["position"]}",
        a["min_overall"] && "overall >= #{a["min_overall"]}",
        a["max_age"] && "age <= #{a["max_age"]}"
      ]
      |> Enum.filter(& &1)

    if parts == [], do: "", else: " (" <> Enum.join(parts, ", ") <> ")"
  end

  defp match_lines(ms, limit) do
    shown = Enum.take(ms, limit)
    [Enum.map(shown, &("- " <> match_text(&1))), more(length(ms) - length(shown))]
  end

  defp more(n) when n > 0, do: "- ... (#{n} more in dataset)"
  defp more(_), do: []

  @doc "One-line description of a match."
  def match_text(%Match{} = m) do
    score =
      if Match.played?(m),
        do: "#{m.home} #{m.home_goals}-#{m.away_goals} #{m.away}",
        else: "#{m.home} vs #{m.away} (no result in dataset)"

    detail =
      [
        "#{m.competition} #{m.season}",
        m.stage,
        m.round && if(m.stage, do: nil, else: "Round #{m.round}"),
        m.arena
      ]
      |> Enum.filter(& &1)
      |> Enum.join(", ")

    "#{Date.to_iso8601(m.date)}: #{score} (#{detail})"
  end

  defp h2h_line(h) do
    "Head-to-head in dataset: #{h.team_a} #{h.record_a.wins} wins, #{h.team_b} #{h.record_b.wins} wins, #{h.record_a.draws} draws"
  end

  defp record_block(title, r) do
    [
      "#{title}:",
      "- Matches: #{r.matches}",
      "- Wins: #{r.wins}, Draws: #{r.draws}, Losses: #{r.losses}",
      "- Goals For: #{r.goals_for}, Goals Against: #{r.goals_against}",
      "- Win rate: #{r.win_rate}%"
    ]
  end

  defp short_record(r) do
    "#{r.matches} matches, #{r.wins}W #{r.draws}D #{r.losses}L, goals #{r.goals_for}-#{r.goals_against}, #{r.points} pts, win rate #{r.win_rate}%"
  end

  defp player_lines(ps, limit) do
    shown = Enum.take(ps, limit)

    [
      shown
      |> Enum.with_index(1)
      |> Enum.map(fn {p, i} ->
        "#{i}. #{p.name} - Overall: #{p.overall}, Potential: #{p.potential}, Position: #{p.position || "n/a"}, Age: #{p.age}, Nationality: #{p.nationality}, Club: #{p.club || "none"}"
      end),
      more(length(ps) - length(shown))
    ]
  end

  defp avg(ps) do
    rated = Enum.filter(ps, & &1.overall)
    Float.round(Enum.sum(Enum.map(rated, & &1.overall)) / max(length(rated), 1), 1)
  end

  defp season_range([]), do: "n/a"
  defp season_range([s]), do: "#{s}"
  defp season_range(seasons), do: "#{List.first(seasons)}-#{List.last(seasons)}"

  defp signed(n) when n > 0, do: "+#{n}"
  defp signed(n), do: "#{n}"

  defp fmt(f, decimals), do: :erlang.float_to_binary(f * 1.0, decimals: decimals)

  defp lines(parts), do: parts |> List.flatten() |> Enum.join("\n")
end
