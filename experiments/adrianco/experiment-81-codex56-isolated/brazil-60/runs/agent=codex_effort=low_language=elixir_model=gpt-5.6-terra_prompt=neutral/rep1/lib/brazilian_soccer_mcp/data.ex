defmodule BrazilianSoccerMcp.Data do
  @moduledoc false
  use Agent
  alias BrazilianSoccerMcp.CSV

  @files %{
    "Brasileirao_Matches.csv" => "Brasileirao",
    "Brazilian_Cup_Matches.csv" => "Copa do Brasil",
    "Libertadores_Matches.csv" => "Libertadores",
    "BR-Football-Dataset.csv" => nil,
    "novo_campeonato_brasileiro.csv" => "Brasileirao"
  }
  def load(dir) do
    stop()

    matches =
      Enum.flat_map(@files, fn {file, competition} ->
        load_matches(Path.join(dir, file), competition)
      end)

    players = CSV.read(Path.join(dir, "fifa_data.csv")) |> Enum.map(&player/1)
    {:ok, _} = Agent.start_link(fn -> %{matches: matches, players: players} end, name: __MODULE__)
    :ok
  end

  defp stop, do: if(Process.whereis(__MODULE__), do: Agent.stop(__MODULE__))
  def all_matches, do: Agent.get(__MODULE__, & &1.matches)
  def players, do: Agent.get(__MODULE__, & &1.players)

  defp load_matches(path, fallback) do
    CSV.read(path)
    |> Enum.map(&match(&1, fallback))
    |> Enum.reject(&(is_nil(&1.home_goal) or is_nil(&1.away_goal)))
  end

  defp match(row, fallback) do
    home = row["home_team"] || row["home"] || row["Equipe_mandante"]
    away = row["away_team"] || row["away"] || row["Equipe_visitante"]
    date = parse_date(row["datetime"] || row["date"] || row["Data"])
    season = integer(row["season"] || row["Ano"]) || year_from_date(date)

    %{
      date: date,
      season: season,
      home_team: home,
      away_team: away,
      home_goal: integer(row["home_goal"] || row["Gols_mandante"]),
      away_goal: integer(row["away_goal"] || row["Gols_visitante"]),
      competition: fallback || row["tournament"],
      round: row["round"] || row["Rodada"],
      stage: row["stage"]
    }
  end

  defp player(row),
    do: %{
      id: row["ID"],
      name: row["Name"],
      nationality: row["Nationality"],
      overall: integer(row["Overall"]),
      potential: integer(row["Potential"]),
      club: row["Club"],
      position: row["Position"],
      age: integer(row["Age"])
    }

  defp integer(nil), do: nil
  defp integer(""), do: nil

  defp integer(s) do
    case Integer.parse(s) do
      {value, _} ->
        value

      :error ->
        case Float.parse(s) do
          {value, _} -> trunc(value)
          :error -> nil
        end
    end
  end

  defp parse_date(nil), do: nil
  defp parse_date(""), do: nil

  defp parse_date(s) do
    s = String.slice(s, 0, 10)

    case String.split(s, "/") do
      [d, m, y] -> "#{y}-#{String.pad_leading(m, 2, "0")}-#{String.pad_leading(d, 2, "0")}"
      _ -> s
    end
  end

  defp year_from_date(<<year::binary-size(4), _::binary>>), do: String.to_integer(year)
  defp year_from_date(_), do: nil
end
