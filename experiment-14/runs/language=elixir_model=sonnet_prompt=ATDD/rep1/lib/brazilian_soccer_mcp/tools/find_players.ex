defmodule BrazilianSoccerMcp.Tools.FindPlayers do
  alias BrazilianSoccerMcp.DataStore

  @default_limit 20

  def call(args) do
    filters = %{
      name: args["name"],
      nationality: args["nationality"],
      club: args["club"],
      position: args["position"],
      min_overall: parse_int(args["min_overall"])
    }

    limit = parse_int(args["limit"]) || @default_limit

    players =
      DataStore.query_players(filters)
      |> Enum.filter(&overall_filter(&1, filters.min_overall))
      |> Enum.sort_by(& &1.overall, :desc)
      |> Enum.take(limit)

    if players == [] do
      {:ok, no_players_message(filters)}
    else
      {:ok, format_players(players, filters)}
    end
  end

  defp overall_filter(_player, nil), do: true
  defp overall_filter(%{overall: overall}, min) when is_integer(overall), do: overall >= min
  defp overall_filter(_player, _min), do: false

  defp format_players(players, filters) do
    header = build_header(filters)

    rows =
      players
      |> Enum.with_index(1)
      |> Enum.map_join("\n", fn {p, idx} ->
        "  #{idx}. #{p.name} — Overall: #{p.overall || "N/A"}, " <>
          "Club: #{p.club}, Nationality: #{p.nationality}"
      end)

    "#{header}\n#{rows}"
  end

  defp build_header(%{name: n, nationality: nat, club: c, min_overall: mo}) do
    parts =
      [
        if(n, do: "Name: #{n}"),
        if(nat, do: "Nationality: #{nat}"),
        if(c, do: "Club: #{c}"),
        if(mo, do: "Min Overall: #{mo}")
      ]
      |> Enum.reject(&is_nil/1)

    if parts == [], do: "Players:", else: "Players matching #{Enum.join(parts, ", ")}:"
  end

  defp no_players_message(%{name: n, nationality: nat, club: c}) do
    desc =
      [if(n, do: "name=#{n}"), if(nat, do: "nationality=#{nat}"), if(c, do: "club=#{c}")]
      |> Enum.reject(&is_nil/1)
      |> Enum.join(", ")

    "No players found for: #{desc}"
  end

  defp parse_int(nil), do: nil
  defp parse_int(i) when is_integer(i), do: i

  defp parse_int(s) when is_binary(s) do
    case Integer.parse(s) do
      {i, _} -> i
      :error -> nil
    end
  end
end
