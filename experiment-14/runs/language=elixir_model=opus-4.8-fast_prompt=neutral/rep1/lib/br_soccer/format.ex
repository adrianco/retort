defmodule BrSoccer.Format do
  @moduledoc "Renders query results as human-readable text, à la the spec examples."

  alias BrSoccer.{Competition, Match}

  @doc "Format a single match as `Home G-G Away` with date and competition context."
  def match_line(%Match{} = m) do
    score =
      if Match.scored?(m),
        do: "#{m.home} #{m.home_goal}-#{m.away_goal} #{m.away}",
        else: "#{m.home} vs #{m.away}"

    "#{date_str(m)}: #{score}#{context(m)}"
  end

  defp context(%Match{} = m) do
    comp = Competition.name(m.competition)

    extra =
      cond do
        m.round -> "Round #{m.round}"
        m.stage -> String.capitalize(m.stage)
        true -> nil
      end

    case extra do
      nil -> " (#{comp})"
      e -> " (#{comp} — #{e})"
    end
  end

  defp date_str(%Match{date: %Date{} = d}), do: Date.to_iso8601(d)
  defp date_str(%Match{season: s}) when is_integer(s), do: "#{s}"
  defp date_str(_), do: "????"

  @doc "Format a list of matches with an optional header and truncation note."
  def matches(list, total, header \\ nil) do
    shown = Enum.map(list, &("- " <> match_line(&1)))

    note =
      if total > length(list),
        do: ["- … (#{total - length(list)} more matches in dataset)"],
        else: []

    lines =
      case list do
        [] -> ["No matches found."]
        _ -> shown ++ note
      end

    prepend(header, lines)
  end

  @doc "Format a head-to-head summary."
  def head_to_head(h) do
    header = "#{h.team_a} vs #{h.team_b} — head-to-head (#{h.total} matches in dataset):"

    recent =
      h.matches
      |> Enum.take(10)
      |> Enum.map(&("- " <> match_line(&1)))

    note =
      if h.total > 10, do: ["- … (#{h.total - 10} more)"], else: []

    summary =
      "\nRecord: #{h.team_a} #{h.a_wins} wins, #{h.team_b} #{h.b_wins} wins, #{h.draws} draws" <>
        "\nGoals: #{h.team_a} #{h.a_goals}, #{h.team_b} #{h.b_goals}"

    body =
      case h.matches do
        [] -> ["No matches found between these clubs."]
        _ -> recent ++ note
      end

    Enum.join([header | body], "\n") <> summary
  end

  @doc "Format a team record."
  def record(r, label) do
    """
    #{label}:
    - Matches: #{r.matches}
    - Wins: #{r.wins}, Draws: #{r.draws}, Losses: #{r.losses}
    - Goals For: #{r.goals_for}, Goals Against: #{r.goals_against} (diff #{sign(r.goal_diff)})
    - Points: #{r.points}
    - Win rate: #{r.win_rate}%\
    """
  end

  defp sign(n) when n > 0, do: "+#{n}"
  defp sign(n), do: "#{n}"

  @doc "Format a league standings table."
  def standings(rows, title) do
    lines =
      Enum.map(rows, fn row ->
        "#{pad(row.position, 2)}. #{row.team} — #{row.points} pts " <>
          "(#{row.wins}W #{row.draws}D #{row.losses}L, GD #{sign(row.goal_diff)})" <>
          champion_tag(row.position)
      end)

    prepend(title, lines)
  end

  defp champion_tag(1), do: " — Champion"
  defp champion_tag(_), do: ""

  @doc "Format a player list."
  def players(list, header \\ nil) do
    lines =
      list
      |> Enum.with_index(1)
      |> Enum.map(fn {p, i} ->
        "#{i}. #{p.name} — Overall: #{p.overall || "?"}, " <>
          "Position: #{p.position || "?"}, Age: #{p.age || "?"}, Club: #{p.club || "Free agent"}"
      end)

    prepend(header, none_if_empty(lines, "No players found."))
  end

  @doc "Format a club-grouped player breakdown."
  def players_by_club(groups, header \\ nil) do
    lines =
      Enum.map(groups, fn g ->
        "- #{g.club}: #{g.count} players (avg rating: #{g.avg_overall})"
      end)

    prepend(header, none_if_empty(lines, "No clubs found."))
  end

  @doc "Format a single player's detail card."
  def player_card(p) do
    """
    #{p.name}
    - Nationality: #{p.nationality}
    - Age: #{p.age}
    - Overall: #{p.overall} (Potential: #{p.potential})
    - Position: #{p.position || "?"}
    - Club: #{p.club || "Free agent"}
    - Height/Weight: #{p.height || "?"} / #{p.weight || "?"}
    - Value: #{p.value || "?"}, Wage: #{p.wage || "?"}\
    """
  end

  @doc "Format biggest wins."
  def biggest_wins(entries, header) do
    lines =
      entries
      |> Enum.with_index(1)
      |> Enum.map(fn {%{match: m, margin: margin}, i} ->
        "#{i}. #{match_line(m)} [margin #{margin}]"
      end)

    prepend(header, none_if_empty(lines, "No matches found."))
  end

  @doc "Format an aggregate stats summary."
  def summary(s, label) do
    """
    #{label}:
    - Matches: #{s.matches}
    - Total goals: #{s.total_goals}
    - Average goals per match: #{s.avg_goals}
    - Home wins: #{s.home_wins} (#{s.home_win_rate}%)
    - Away wins: #{s.away_wins} (#{s.away_win_rate}%)
    - Draws: #{s.draws} (#{s.draw_rate}%)\
    """
  end

  @doc "Format a team's competition appearances."
  def competitions(list, team) do
    lines =
      Enum.map(list, fn c ->
        seasons = season_range(c.seasons)
        "- #{Competition.name(c.competition)}: #{c.matches} matches#{seasons}"
      end)

    prepend("Competitions for #{team}:", none_if_empty(lines, "No matches found."))
  end

  defp season_range([]), do: ""
  defp season_range(seasons), do: " (#{List.first(seasons)}–#{List.last(seasons)})"

  # ---- helpers ----

  defp prepend(nil, lines), do: Enum.join(lines, "\n")
  defp prepend(header, lines), do: Enum.join([header | lines], "\n")

  defp none_if_empty([], msg), do: [msg]
  defp none_if_empty(lines, _msg), do: lines

  defp pad(n, width), do: String.pad_leading(to_string(n), width)
end
