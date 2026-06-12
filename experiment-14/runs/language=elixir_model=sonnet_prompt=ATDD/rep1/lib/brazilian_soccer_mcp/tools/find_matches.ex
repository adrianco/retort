defmodule BrazilianSoccerMcp.Tools.FindMatches do
  alias BrazilianSoccerMcp.DataStore

  @default_limit 20

  def call(args) do
    filters = %{
      team1: args["team1"],
      team2: args["team2"],
      season: parse_int(args["season"]),
      competition: args["competition"]
    }

    limit = parse_int(args["limit"]) || @default_limit

    matches =
      DataStore.query_matches(filters)
      |> Enum.sort_by(& &1.date || "", :desc)
      |> Enum.uniq_by(&{&1.home, &1.away, &1.date, &1.competition})
      |> Enum.take(limit)

    if matches == [] do
      {:ok, no_matches_message(filters)}
    else
      {:ok, format_matches(matches, filters)}
    end
  end

  defp format_matches(matches, filters) do
    header = build_header(filters)

    rows =
      matches
      |> Enum.map_join("\n", fn m ->
        "  #{format_date(m.date)}: #{m.home} #{m.home_goal}-#{m.away_goal} #{m.away}" <>
          "  [#{m.competition}#{round_suffix(m.round)}]"
      end)

    summary = head_to_head_summary(matches, filters)

    [header, rows, summary]
    |> Enum.reject(&(&1 == ""))
    |> Enum.join("\n")
  end

  defp build_header(%{team1: t1, team2: t2, season: s, competition: c}) do
    parts =
      [
        team_label(t1, t2),
        if(c, do: c, else: nil),
        if(s, do: "Season #{s}", else: nil)
      ]
      |> Enum.reject(&is_nil/1)

    "Matches: " <> Enum.join(parts, " | ")
  end

  defp team_label(nil, nil), do: "All teams"
  defp team_label(t1, nil), do: t1
  defp team_label(t1, t2), do: "#{t1} vs #{t2}"

  defp round_suffix(nil), do: ""
  defp round_suffix(r) when is_binary(r), do: ", #{r}"
  defp round_suffix(r), do: ", Round #{r}"

  defp head_to_head_summary(_matches, %{team1: nil}), do: ""
  defp head_to_head_summary(_matches, %{team2: nil}), do: ""

  defp head_to_head_summary(matches, %{team1: t1, team2: t2}) do
    t1_down = String.downcase(t1)
    t2_down = String.downcase(t2)

    {t1_wins, t2_wins, draws} =
      Enum.reduce(matches, {0, 0, 0}, fn m, {w1, w2, d} ->
        home_is_t1 = String.contains?(String.downcase(m.home), t1_down)
        home_is_t2 = String.contains?(String.downcase(m.home), t2_down)

        {winner_is_t1, winner_is_t2} =
          cond do
            m.home_goal == m.away_goal -> {false, false}
            m.home_goal > m.away_goal and home_is_t1 -> {true, false}
            m.home_goal > m.away_goal and home_is_t2 -> {false, true}
            m.away_goal > m.home_goal and home_is_t1 -> {false, true}
            m.away_goal > m.home_goal and home_is_t2 -> {true, false}
            true -> {false, false}
          end

        cond do
          winner_is_t1 -> {w1 + 1, w2, d}
          winner_is_t2 -> {w1, w2 + 1, d}
          m.home_goal == m.away_goal -> {w1, w2, d + 1}
          true -> {w1, w2, d}
        end
      end)

    "\nHead-to-head: #{t1} #{t1_wins} wins, #{t2} #{t2_wins} wins, #{draws} draws"
  end

  defp no_matches_message(%{team1: t1, team2: t2, season: s, competition: c}) do
    desc =
      [t1, t2, if(s, do: "season #{s}"), c]
      |> Enum.reject(&is_nil/1)
      |> Enum.join(", ")

    "No matches found for: #{desc}"
  end

  defp format_date(nil), do: "unknown date"
  defp format_date(d) when is_binary(d), do: d

  defp parse_int(nil), do: nil
  defp parse_int(i) when is_integer(i), do: i

  defp parse_int(s) when is_binary(s) do
    case Integer.parse(s) do
      {i, _} -> i
      :error -> nil
    end
  end
end
