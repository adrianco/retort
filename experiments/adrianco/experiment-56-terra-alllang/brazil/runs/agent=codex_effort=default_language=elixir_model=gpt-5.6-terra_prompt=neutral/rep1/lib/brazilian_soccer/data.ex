defmodule BrazilianSoccer.Data do
  @moduledoc false
  alias BrazilianSoccer.{CSV, Normalize}

  def load(path) do
    %{
      matches:
        match_sources(path)
        |> Enum.flat_map(fn {file, competition, mapper} ->
          path |> Path.join(file) |> CSV.read() |> Enum.map(&safe_match(mapper, &1, competition)) |> Enum.reject(&is_nil/1)
        end),
      players: path |> Path.join("fifa_data.csv") |> CSV.read() |> Enum.map(&player/1)
    }
  end

  defp match_sources(_),
    do: [
      {"Brasileirao_Matches.csv", "Brasileirão", &standard/2},
      {"Brazilian_Cup_Matches.csv", "Copa do Brasil", &standard/2},
      {"Libertadores_Matches.csv", "Libertadores", &standard/2},
      {"BR-Football-Dataset.csv", "Extended Statistics", &extended/2},
      {"novo_campeonato_brasileiro.csv", "Brasileirão", &historical/2}
    ]

  defp standard(r, competition),
    do:
      match(
        r["home_team"],
        r["away_team"],
        r["home_goal"],
        r["away_goal"],
        r["datetime"],
        r["season"],
        competition,
        r["round"] || r["stage"],
        r
      )

  defp extended(r, _),
    do:
      match(
        r["home"],
        r["away"],
        r["home_goal"],
        r["away_goal"],
        r["date"],
        year(r["date"]),
        r["tournament"],
        nil,
        r
      )

  defp historical(r, competition),
    do:
      match(
        r["Equipe_mandante"],
        r["Equipe_visitante"],
        r["Gols_mandante"],
        r["Gols_visitante"],
        r["Data"],
        r["Ano"],
        competition,
        r["Rodada"],
        r
      )

  defp match(home, away, hg, ag, date, season, competition, stage, raw),
    do: %{
      home: Normalize.display_team(home),
      away: Normalize.display_team(away),
      home_key: Normalize.team(home),
      away_key: Normalize.team(away),
      home_goals: integer(hg),
      away_goals: integer(ag),
      date: Normalize.date!(date),
      season: integer(season),
      competition: competition,
      stage: stage,
      raw: raw
    }

  defp player(r),
    do: %{
      id: r["ID"],
      name: r["Name"],
      age: integer(r["Age"]),
      nationality: r["Nationality"],
      overall: integer(r["Overall"]),
      potential: integer(r["Potential"]),
      club: r["Club"],
      position: r["Position"],
      jersey_number: integer(r["Jersey Number"]),
      raw: r
    }

  defp integer(nil), do: 0
  defp integer(""), do: 0
  defp integer("NA"), do: nil
  defp integer("-"), do: nil

  defp integer(value) do
    case Float.parse(to_string(value)) do
      {n, _} -> trunc(n)
      :error -> 0
    end
  end

  defp year(date), do: date |> Normalize.date!() |> Map.fetch!(:year)
  defp safe_match(mapper, row, competition) do
    mapper.(row, competition)
  rescue
    ArgumentError -> nil
  end
end
