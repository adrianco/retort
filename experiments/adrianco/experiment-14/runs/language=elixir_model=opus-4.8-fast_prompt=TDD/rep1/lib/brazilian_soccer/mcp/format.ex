defmodule BrazilianSoccer.MCP.Format do
  @moduledoc """
  Human-readable rendering of query results for MCP text responses.
  """

  alias BrazilianSoccer.Match

  @doc "One-line description of a match."
  @spec match_line(Match.t()) :: String.t()
  def match_line(%Match{} = m) do
    "#{date(m.date)}: #{m.home_team} #{score(m)} #{m.away_team}#{context(m)}"
  end

  @doc "Render a list of matches, truncated to `limit` with a remainder note."
  @spec matches(list(Match.t()), pos_integer()) :: String.t()
  def matches(matches, limit \\ 15) do
    shown = Enum.take(matches, limit)
    extra = length(matches) - length(shown)

    lines = Enum.map_join(shown, "\n", &("- " <> match_line(&1)))
    if extra > 0, do: lines <> "\n- ... (#{extra} more)", else: lines
  end

  @doc "Render a head-to-head summary."
  @spec head_to_head(map()) :: String.t()
  def head_to_head(h2h) do
    "Head-to-head in dataset: #{h2h.team_a} #{h2h.a_wins} wins, " <>
      "#{h2h.team_b} #{h2h.b_wins} wins, #{h2h.draws} draws " <>
      "(goals #{h2h.a_goals}-#{h2h.b_goals})"
  end

  @doc "Render a team record block."
  @spec record(map(), String.t()) :: String.t()
  def record(r, title) do
    """
    #{title}:
    - Matches: #{r.played}
    - Wins: #{r.wins}, Draws: #{r.draws}, Losses: #{r.losses}
    - Goals For: #{r.goals_for}, Goals Against: #{r.goals_against} (GD #{signed(r.goal_difference)})
    - Points: #{r.points}
    - Win rate: #{percent(r.win_rate)}
    """
    |> String.trim_trailing()
  end

  @doc "Render a standings table."
  @spec standings([map()], String.t()) :: String.t()
  def standings(table, title) do
    rows =
      Enum.map_join(table, "\n", fn row ->
        "#{row.position}. #{row.team} - #{row.points} pts " <>
          "(#{row.wins}W, #{row.draws}D, #{row.losses}L, GD #{signed(row.goal_difference)})"
      end)

    "#{title}:\n#{rows}"
  end

  @doc "Render a player line."
  @spec player_line(map() | struct(), non_neg_integer() | nil) :: String.t()
  def player_line(p, rank \\ nil) do
    prefix = if rank, do: "#{rank}. ", else: "- "

    prefix <>
      "#{p.name} - Overall: #{p.overall || "?"}, Position: #{p.position || "?"}, " <>
      "Club: #{p.club || "?"}#{nationality(p)}"
  end

  @doc "Render a list of players, optionally numbered."
  @spec players([struct()]) :: String.t()
  def players(players) do
    players
    |> Enum.with_index(1)
    |> Enum.map_join("\n", fn {p, i} -> player_line(p, i) end)
  end

  @doc "Format a float as a percentage string."
  @spec percent(float()) :: String.t()
  def percent(rate), do: "#{Float.round(rate * 100, 1)}%"

  defp nationality(%{nationality: nil}), do: ""
  defp nationality(%{nationality: nat}), do: ", Nationality: #{nat}"
  defp nationality(_), do: ""

  defp score(%Match{home_goals: h, away_goals: a}) when is_integer(h) and is_integer(a),
    do: "#{h}-#{a}"

  defp score(_), do: "vs"

  defp context(%Match{} = m) do
    parts =
      [m.competition, round_or_stage(m), season(m)]
      |> Enum.reject(&is_nil/1)

    case parts do
      [] -> ""
      list -> " (" <> Enum.join(list, ", ") <> ")"
    end
  end

  defp round_or_stage(%Match{round: nil, stage: nil}), do: nil
  defp round_or_stage(%Match{round: nil, stage: stage}), do: stage
  defp round_or_stage(%Match{round: round}), do: "Round #{round}"

  defp season(%Match{season: nil}), do: nil
  defp season(%Match{season: s}), do: Integer.to_string(s)

  defp date(nil), do: "date unknown"
  defp date(%Date{} = d), do: Date.to_iso8601(d)

  defp signed(n) when n > 0, do: "+#{n}"
  defp signed(n), do: Integer.to_string(n)
end
