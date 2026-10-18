defmodule SoccerMcp.Format do
  @moduledoc """
  Renders query results as plain text for the LLM, following the answer
  formats in the specification (one fact per line, scores as `A 2-1 B`).
  """

  alias SoccerMcp.{Match, Player, Query, Team}

  @doc "One match as `YYYY-MM-DD: Home 2-1 Away (Competition, stage, season)`."
  @spec match_line(Match.t()) :: String.t()
  def match_line(%Match{} = m) do
    details =
      [m.competition, m.stage, to_string(m.season)]
      |> Enum.reject(&is_nil/1)
      |> Enum.join(", ")

    "#{Date.to_iso8601(m.date)}: #{m.home} #{m.home_goals}-#{m.away_goals} #{m.away} (#{details})"
  end

  @doc """
  A list of matches with a header line, capped at `limit`, and a trailing
  note with the number not shown.
  """
  @spec match_list([Match.t()], non_neg_integer()) :: String.t()
  def match_list([], _limit), do: "No matches found in the dataset."

  def match_list(matches, limit) do
    shown = Enum.take(matches, limit)
    rest = length(matches) - length(shown)

    lines = Enum.map(shown, &("- " <> match_line(&1)))
    note = if rest > 0, do: ["- ... (#{rest} more matches in dataset)"], else: []

    Enum.join(["Matches found: #{length(matches)}" | lines] ++ note, "\n")
  end

  @doc "Win, draw and loss summary for one team."
  @spec record_summary(String.t(), map()) :: String.t()
  def record_summary(name, rec) do
    """
    #{name}:
    - Matches: #{rec.played}
    - Wins: #{rec.wins}, Draws: #{rec.draws}, Losses: #{rec.losses}
    - Goals For: #{rec.goals_for}, Goals Against: #{rec.goals_against}
    - Win rate: #{rec.win_rate}%
    """
    |> String.trim_trailing()
  end

  @doc "Head-to-head summary between two teams, from matches they played each other in."
  @spec head_to_head_summary([Match.t()], String.t(), String.t()) :: String.t()
  def head_to_head_summary([], team_a, team_b),
    do: "Head-to-head in dataset: no matches between #{team_a} and #{team_b}."

  def head_to_head_summary(matches, team_a, team_b) do
    key_a = Team.key(team_a)
    rec = Query.record(matches, key_a)
    name_a = name_for(matches, key_a, team_a)
    name_b = name_for(matches, Team.key(team_b), team_b)

    "Head-to-head in dataset: #{name_a} #{rec.wins} wins, #{name_b} #{rec.losses} wins, #{rec.draws} draws"
  end

  # The display name the dataset uses for a team key, falling back to the query.
  defp name_for(matches, key, fallback) do
    Enum.find_value(matches, fallback, fn m ->
      cond do
        m.home_key == key -> m.home
        m.away_key == key -> m.away
        true -> nil
      end
    end)
  end

  @doc "League table for a competition and season."
  @spec standings_table([map()], String.t(), integer()) :: String.t()
  def standings_table([], competition, season),
    do: "No #{competition} matches found for #{season}."

  def standings_table(rows, competition, season) do
    header = "#{season} #{competition} standings (calculated from matches):"

    lines =
      rows
      |> Enum.with_index(1)
      |> Enum.map(fn {row, pos} ->
        "#{pos}. #{row.team} - #{row.points} pts (#{row.wins}W, #{row.draws}D, #{row.losses}L) GF #{row.goals_for} GA #{row.goals_against} GD #{signed(row.goal_difference)}"
      end)

    Enum.join([header | lines], "\n")
  end

  @doc "Summary statistics block from `Query.averages/1`."
  @spec averages(map(), String.t()) :: String.t()
  def averages(stats, label) do
    """
    #{label}:
    - Matches: #{stats.matches}
    - Average goals per match: #{stats.goals_per_match}
    - Home win rate: #{stats.home_win_rate}%
    - Draw rate: #{stats.draw_rate}%
    - Away win rate: #{stats.away_win_rate}%
    """
    |> String.trim_trailing()
  end

  @doc "Numbered list of the biggest wins."
  @spec biggest_wins([Match.t()]) :: String.t()
  def biggest_wins([]), do: "No decisive matches found."

  def biggest_wins(matches) do
    lines =
      matches
      |> Enum.with_index(1)
      |> Enum.map(fn {m, i} -> "#{i}. #{match_line(m)}" end)

    Enum.join(["Biggest wins (by margin):" | lines], "\n")
  end

  @doc "Numbered venue ranking, e.g. best home or away record."
  @spec venue_ranking([map()], String.t()) :: String.t()
  def venue_ranking([], label), do: "No teams with enough #{label} matches to rank."

  def venue_ranking(rows, label) do
    lines =
      rows
      |> Enum.take(10)
      |> Enum.with_index(1)
      |> Enum.map(fn {r, i} ->
        "#{i}. #{r.team} - #{r.win_rate}% wins (#{r.wins}W #{r.draws}D #{r.losses}L in #{r.played} #{label} matches)"
      end)

    Enum.join(["Best #{label} records:" | lines], "\n")
  end

  @doc "Player list with ratings, club and position."
  @spec players([Player.t()]) :: String.t()
  def players([]), do: "No players found in the dataset."

  def players(players) do
    lines =
      players
      |> Enum.with_index(1)
      |> Enum.map(fn {p, i} ->
        "#{i}. #{p.name} - Overall: #{p.overall}, Position: #{p.position || "?"}, Club: #{p.club || "none listed"}, Nationality: #{p.nationality || "?"}, Age: #{p.age || "?"}"
      end)

    Enum.join(["Players found: #{length(players)}" | lines], "\n")
  end

  defp signed(n) when n > 0, do: "+#{n}"
  defp signed(n), do: "#{n}"
end
