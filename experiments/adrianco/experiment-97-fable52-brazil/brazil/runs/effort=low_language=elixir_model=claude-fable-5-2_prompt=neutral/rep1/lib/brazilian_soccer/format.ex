defmodule BrazilianSoccer.Format do
  @moduledoc "Plain-text rendering of query results for MCP tool responses."

  alias BrazilianSoccer.Queries

  def match(m) do
    "#{m.date}: #{m.home_name} #{m.home_goals}-#{m.away_goals} #{m.away_name} (#{context(m)})"
  end

  def context(m) do
    detail =
      cond do
        m.stage -> ", " <> m.stage
        m.round -> ", Round #{m.round}"
        true -> ""
      end

    "#{m.competition} #{m.season}#{detail}"
  end

  def match_detail(m) do
    extras =
      [
        m.time && "kick-off #{m.time}",
        m.arena && "stadium: #{m.arena}",
        m.stats[:home_corners] && "corners #{m.stats[:home_corners]}-#{m.stats[:away_corners]}",
        m.stats[:home_shots] && "shots #{m.stats[:home_shots]}-#{m.stats[:away_shots]}"
      ]
      |> Enum.filter(& &1)

    if extras == [], do: match(m), else: match(m) <> " [" <> Enum.join(extras, "; ") <> "]"
  end

  @doc "Bulleted match list truncated to `limit` with a `... (N more)` trailer."
  def match_list(matches, limit, fun \\ &match/1) do
    shown = Enum.take(matches, limit)
    more = length(matches) - length(shown)
    lines = Enum.map(shown, &("- " <> fun.(&1)))
    lines = if more > 0, do: lines ++ ["- ... (#{more} more matches in dataset)"], else: lines
    Enum.join(lines, "\n")
  end

  def record(r) do
    """
    - Matches: #{r.matches}
    - Wins: #{r.wins}, Draws: #{r.draws}, Losses: #{r.losses}
    - Goals For: #{r.goals_for}, Goals Against: #{r.goals_against} (difference #{signed(r.goal_difference)})
    - Points: #{r.points} (#{r.points_per_game} per game)
    - Win rate: #{r.win_rate}%\
    """
  end

  def record_line(r) do
    "#{r.matches} matches, #{r.wins}W #{r.draws}D #{r.losses}L, goals #{r.goals_for}-#{r.goals_against}, win rate #{r.win_rate}%"
  end

  def signed(n) when n > 0, do: "+#{n}"
  def signed(n), do: "#{n}"

  def head_to_head(h) do
    "Head-to-head in dataset (#{h.total} matches): #{h.team_a} #{h.a_wins} wins, #{h.team_b} #{h.b_wins} wins, #{h.draws} draws" <>
      " (goals: #{h.team_a} #{h.a_goals}, #{h.team_b} #{h.b_goals})"
  end

  def standings(s) do
    header =
      "#{s.season} #{s.competition} standings (calculated from #{s.matches} match results):"

    rows =
      Enum.map(s.rows, fn r ->
        note = if r.note, do: " - #{r.note}", else: ""

        "#{r.position}. #{r.team} - #{r.points} pts (#{r.wins}W, #{r.draws}D, #{r.losses}L), " <>
          "goals #{r.goals_for}-#{r.goals_against} (#{signed(r.goal_difference)}), #{r.matches} played#{note}"
      end)

    footer =
      if s.complete,
        do:
          "Note: points are computed from results only (3 per win); sporting-court point deductions are not in the data.",
        else:
          "Note: the dataset does not contain every match of this season, so no champion/relegation is marked."

    Enum.join([header | rows] ++ ["", footer], "\n")
  end

  def summary(s) do
    """
    - Matches: #{s.matches}
    - Goals: #{s.goals} (home #{s.home_goals}, away #{s.away_goals})
    - Average goals per match: #{s.avg_goals}
    - Home wins: #{s.home_wins} (#{s.home_win_rate}%), Draws: #{s.draws} (#{s.draw_rate}%), Away wins: #{s.away_wins} (#{s.away_win_rate}%)\
    """
  end

  def player(p) do
    "#{p.name} - Overall: #{p.overall}, Potential: #{p.potential}, Position: #{p.position || "n/a"}, " <>
      "Age: #{p.age}, Nationality: #{p.nationality}, Club: #{p.club || "none"}"
  end

  def player_detail(p) do
    top =
      p.attributes
      |> Enum.sort_by(fn {k, v} -> {-v, k} end)
      |> Enum.take(8)
      |> Enum.map_join(", ", fn {k, v} -> "#{k} #{v}" end)

    """
    #{p.name} (FIFA id #{p.id})
    - Nationality: #{p.nationality}, Age: #{p.age}
    - Club: #{p.club || "none"}, Position: #{p.position || "n/a"}, Jersey: #{p.jersey || "n/a"}
    - Overall: #{p.overall}, Potential: #{p.potential}
    - Height: #{p.height || "n/a"}, Weight: #{p.weight || "n/a"}, Preferred foot: #{p.foot || "n/a"}
    - Value: #{p.value || "n/a"}, Wage: #{p.wage || "n/a"}
    - Best attributes: #{top}\
    """
  end

  def numbered(items, fun) do
    items |> Enum.with_index(1) |> Enum.map_join("\n", fn {x, i} -> "#{i}. #{fun.(x)}" end)
  end

  def round_label(m), do: Queries.round_label(m)
end
