defmodule BrazilianSoccerMcp.Format do
  @moduledoc """
  Renders query results as the human-readable text returned in MCP tool
  responses, following the answer formats in the specification.
  """

  alias BrazilianSoccerMcp.{DataStore, Queries}

  @doc "One line per match: `- 2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A Round 22)`."
  def match_line(m) do
    home = DataStore.display(m.home_key)
    away = DataStore.display(m.away_key)
    score = if m.home_goal && m.away_goal, do: "#{m.home_goal}-#{m.away_goal}", else: "vs"
    "- #{m.date}: #{home} #{score} #{away} (#{context(m)})"
  end

  defp context(m) do
    label = Queries.competition_label(m.competition)

    detail =
      cond do
        m.stage not in [nil, ""] -> " #{m.stage}"
        m.round not in [nil, ""] -> " Round #{m.round}"
        true -> ""
      end

    "#{label}#{detail}"
  end

  @doc "Format a match list with a header, truncated to `limit` lines."
  def matches(matches, header, limit \\ 20) do
    shown = Enum.take(matches, limit)
    rest = length(matches) - length(shown)

    lines =
      [header <> ":"] ++
        Enum.map(shown, &match_line/1) ++
        if(rest > 0, do: ["... (#{rest} more matches in dataset)"], else: [])

    case matches do
      [] -> header <> ": no matches found in the dataset."
      _ -> Enum.join(lines, "\n")
    end
  end

  def head_to_head(name1, name2, %{matches: matches, summary: s}, limit \\ 15) do
    if matches == [] do
      "No matches found between #{name1} and #{name2} in the dataset."
    else
      matches(matches, "#{name1} vs #{name2}", limit) <>
        "\n\nHead-to-head in dataset (#{length(matches)} matches): " <>
        "#{name1} #{s.team1_wins} wins, #{name2} #{s.team2_wins} wins, #{s.draws} draws. " <>
        "Goals: #{name1} #{s.team1_goals}, #{name2} #{s.team2_goals}."
    end
  end

  def team_stats(team_name, result, opts \\ []) do
    %{stats: s, by_competition: by_comp, keys: keys} = result

    if s.played == 0 do
      "No matches found for #{team_name} with the given filters."
    else
      display = keys |> Enum.map(&DataStore.display/1) |> Enum.sort() |> Enum.join(" / ")

      qualifier =
        [
          opts[:season] && "#{opts[:season]}",
          opts[:competition] && to_string(opts[:competition]),
          opts[:venue] in [:home, :away] && "#{opts[:venue]} matches only"
        ]
        |> Enum.filter(& &1)
        |> case do
          [] -> ""
          parts -> " (" <> Enum.join(parts, ", ") <> ")"
        end

      comp_lines =
        for {comp, cs} <- Enum.sort_by(by_comp, fn {_c, cs} -> -cs.played end) do
          "  - #{Queries.competition_label(comp)}: #{cs.played} matches, " <>
            "#{cs.wins}W #{cs.draws}D #{cs.losses}L, GF #{cs.goals_for} GA #{cs.goals_against}"
        end

      """
      #{display} record#{qualifier}:
      - Matches: #{s.played}
      - Wins: #{s.wins}, Draws: #{s.draws}, Losses: #{s.losses}
      - Goals For: #{s.goals_for}, Goals Against: #{s.goals_against}
      - Win rate: #{Queries.percent(s.wins, s.played)}%

      By competition:
      #{Enum.join(comp_lines, "\n")}
      """
      |> String.trim_trailing()
    end
  end

  def standings(season, competition, rows, limit \\ 20) do
    if rows == [] do
      "No #{Queries.competition_label(competition)} matches found for season #{season}."
    else
      lines =
        rows
        |> Enum.take(limit)
        |> Enum.with_index(1)
        |> Enum.map(fn {r, pos} ->
          champion = if pos == 1, do: " - Champion", else: ""

          "#{String.pad_leading(to_string(pos), 2)}. #{r.team} - #{r.points} pts " <>
            "(#{r.wins}W, #{r.draws}D, #{r.losses}L, GD #{signed(r.goal_diff)}, GF #{r.goals_for})#{champion}"
        end)

      "#{season} #{Queries.competition_label(competition)} Standings (calculated from matches):\n" <>
        Enum.join(lines, "\n")
    end
  end

  defp signed(n) when n > 0, do: "+#{n}"
  defp signed(n), do: to_string(n)

  def players(players, header) do
    if players == [] do
      header <>
        ": no players found. Note: the FIFA dataset does not include every club " <>
        "(several Brazilian clubs such as Flamengo, Palmeiras, Corinthians and São Paulo " <>
        "are absent from FIFA 19 licensing)."
    else
      lines =
        players
        |> Enum.with_index(1)
        |> Enum.map(fn {p, i} ->
          "#{i}. #{p.name} - Overall: #{p.overall}, Position: #{p.position || "?"}, " <>
            "Club: #{p.club || "Free agent"}, Age: #{p.age}, Nationality: #{p.nationality}"
        end)

      header <> ":\n" <> Enum.join(lines, "\n")
    end
  end

  def player_details(p) do
    top_skills =
      p.skills
      |> Enum.sort_by(fn {_k, v} -> -v end)
      |> Enum.take(5)
      |> Enum.map(fn {k, v} -> "#{k} #{v}" end)
      |> Enum.join(", ")

    """
    #{p.name}
    - Overall: #{p.overall} (Potential: #{p.potential})
    - Position: #{p.position || "?"}, Jersey: #{p.jersey_number || "?"}
    - Club: #{p.club || "Free agent"}
    - Nationality: #{p.nationality}, Age: #{p.age}
    - Height: #{p.height || "?"}, Weight: #{p.weight || "?"}, Preferred foot: #{p.preferred_foot || "?"}
    - Value: #{p.value || "?"}, Wage: #{p.wage || "?"}
    - Top skills: #{top_skills}
    """
    |> String.trim_trailing()
  end

  def biggest_wins(matches, header) do
    if matches == [] do
      header <> ": no matches found."
    else
      lines =
        matches
        |> Enum.with_index(1)
        |> Enum.map(fn {m, i} ->
          home = DataStore.display(m.home_key)
          away = DataStore.display(m.away_key)

          "#{i}. #{m.date}: #{home} #{m.home_goal}-#{m.away_goal} #{away} " <>
            "(#{Queries.competition_label(m.competition)})"
        end)

      header <> ":\n" <> Enum.join(lines, "\n")
    end
  end

  def competition_stats(stats, header) do
    if stats.matches == 0 do
      header <> ": no matches found."
    else
      """
      #{header}:
      - Matches: #{stats.matches}
      - Total goals: #{stats.total_goals}
      - Average goals per match: #{stats.avg_goals}
      - Home wins: #{stats.home_wins} (#{stats.home_win_rate}%)
      - Draws: #{stats.draws} (#{stats.draw_rate}%)
      - Away wins: #{stats.away_wins} (#{stats.away_win_rate}%)
      """
      |> String.trim_trailing()
    end
  end
end
