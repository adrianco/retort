defmodule BrasilSoccer.Formatter do
  @moduledoc """
  Renders query results as the human-readable text the MCP tools return to the
  LLM, following the answer shapes described in the project specification.
  """

  alias BrasilSoccer.Match

  @doc "One line describing a single match."
  @spec match_line(Match.t()) :: String.t()
  def match_line(%Match{} = m) do
    "#{date(m.date)}: #{m.home_team} #{score(m)} #{m.away_team} (#{context(m)})"
  end

  defp score(%Match{home_goal: h, away_goal: a}) when is_integer(h) and is_integer(a),
    do: "#{h}-#{a}"

  defp score(_), do: "vs"

  defp context(%Match{competition: comp, round: round, stage: stage}) do
    cond do
      round not in [nil, ""] -> "#{comp} Round #{round}"
      stage not in [nil, ""] -> "#{comp}, #{stage}"
      true -> to_string(comp)
    end
  end

  @doc "A titled, counted list of matches."
  @spec matches([Match.t()], String.t()) :: String.t()
  def matches([], title), do: "#{title}\nNo matches found in the dataset."

  def matches(list, title) do
    body = list |> Enum.map(&("- " <> match_line(&1))) |> Enum.join("\n")
    "#{title}:\n#{body}\n\n#{count(length(list), "match", "matches")} found."
  end

  @doc "Head-to-head summary text."
  @spec head_to_head(map()) :: String.t()
  def head_to_head(h2h) do
    header = "#{h2h.team_a} vs #{h2h.team_b} head-to-head (in dataset):"

    summary =
      "#{h2h.team_a} #{count(h2h.a_wins, "win", "wins")}, " <>
        "#{h2h.team_b} #{count(h2h.b_wins, "win", "wins")}, " <>
        "#{count(h2h.draws, "draw", "draws")} (#{h2h.total} total)"

    lines =
      h2h.matches
      |> Enum.take(15)
      |> Enum.map(&("- " <> match_line(&1)))
      |> Enum.join("\n")

    [header, summary, "", lines] |> Enum.reject(&(&1 == "")) |> Enum.join("\n")
  end

  @doc "Team record block."
  @spec record(map()) :: String.t()
  def record(rec) do
    """
    #{rec.team} record (in dataset):
    - Matches: #{rec.played}
    - Wins: #{rec.wins}, Draws: #{rec.draws}, Losses: #{rec.losses}
    - Goals For: #{rec.goals_for}, Goals Against: #{rec.goals_against} (diff #{format_diff(rec.goal_difference)})
    - Win rate: #{rec.win_rate}%\
    """
  end

  @doc "Comparison of two teams."
  @spec compare(map()) :: String.t()
  def compare(cmp) do
    [
      head_to_head(cmp.head_to_head),
      "",
      record(cmp.record_a),
      "",
      record(cmp.record_b)
    ]
    |> Enum.join("\n")
  end

  @doc "Standings table."
  @spec standings([map()], String.t(), integer()) :: String.t()
  def standings([], competition, season),
    do: "No #{competition} matches found for #{season}."

  def standings(table, competition, season) do
    rows =
      Enum.map(table, fn r ->
        "#{r.position}. #{r.team} - #{r.points} pts " <>
          "(#{r.wins}W #{r.draws}D #{r.losses}L, " <>
          "#{r.goals_for}-#{r.goals_against}, diff #{format_diff(r.goal_difference)})"
      end)

    "#{season} #{competition} standings (calculated from match results):\n" <>
      Enum.join(rows, "\n")
  end

  @doc "Player list."
  @spec players([map()], String.t()) :: String.t()
  def players([], title), do: "#{title}\nNo players found in the dataset."

  def players(list, title) do
    rows =
      list
      |> Enum.with_index(1)
      |> Enum.map(fn {p, i} ->
        "#{i}. #{p.name} - Overall: #{p.overall}, Position: #{p.position}, " <>
          "Club: #{p.club}, Nationality: #{p.nationality}"
      end)

    "#{title}:\n" <> Enum.join(rows, "\n")
  end

  @doc "Per-club player summary."
  @spec club_summary([map()], String.t()) :: String.t()
  def club_summary([], title), do: "#{title}\nNo players found in the dataset."

  def club_summary(list, title) do
    rows =
      Enum.map(list, fn s ->
        "- #{s.club}: #{count(s.count, "player", "players")} (avg rating: #{s.avg_overall})"
      end)

    "#{title}:\n" <> Enum.join(rows, "\n")
  end

  @doc "Aggregate statistics summary."
  @spec summary(map(), String.t()) :: String.t()
  def summary(s, title) do
    """
    #{title}:
    - Matches: #{s.matches}
    - Total goals: #{s.total_goals}
    - Average goals per match: #{s.avg_goals}
    - Home wins: #{s.home_wins} (#{s.home_win_rate}%), Away wins: #{s.away_wins} (#{s.away_win_rate}%), Draws: #{s.draws} (#{s.draw_rate}%)\
    """
  end

  defp date(%Date{} = d), do: Date.to_iso8601(d)
  defp date(_), do: "unknown date"

  defp format_diff(n) when n > 0, do: "+#{n}"
  defp format_diff(n), do: "#{n}"

  defp count(1, singular, _plural), do: "1 #{singular}"
  defp count(n, _singular, plural), do: "#{n} #{plural}"
end
