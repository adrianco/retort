defmodule BrazilianSoccerMcp.DataLoader do
  @moduledoc """
  Loads the Kaggle CSV files in `data/kaggle/` into `Match` and `Player` structs.

  Five match files are merged. The Brasileirão and cup files overlap, and
  they sometimes disagree on a match date by a day. So a match is identified
  by (competition, season, home, away). The n-th occurrence of that identity
  within one file is matched with the n-th occurrence in the other files, and
  only one copy is kept. Repeats inside a single file, such as state-league
  return rounds, are all kept. Rows with an unparseable date or score are skipped.
  """

  alias BrazilianSoccerMcp.{CSV, Competition, Match, Player, TeamName}

  @iso_date ~r/^(\d{4})-(\d{2})-(\d{2})/
  @br_date ~r|^(\d{2})/(\d{2})/(\d{4})|

  @doc "Loads and merges every match file found in `dir`."
  @spec load_matches(Path.t()) :: [Match.t()]
  def load_matches(dir) do
    files =
      [
        {"Brasileirao_Matches.csv", &from_brasileirao/1},
        {"novo_campeonato_brasileiro.csv", &from_historical/1},
        {"Brazilian_Cup_Matches.csv", &from_cup/1},
        {"Libertadores_Matches.csv", &from_libertadores/1},
        {"BR-Football-Dataset.csv", &from_br_football/1}
      ]
      |> Enum.map(fn {file, mapper} ->
        dir |> read_rows(file) |> Enum.map(mapper) |> Enum.reject(&is_nil/1)
      end)

    index = files |> List.flatten() |> Match.state_index()

    files
    |> Enum.flat_map(fn matches ->
      matches |> Enum.map(&Match.qualify(&1, index)) |> number_occurrences()
    end)
    |> Enum.uniq_by(fn {occurrence_key, _match} -> occurrence_key end)
    |> Enum.map(fn {_occurrence_key, match} -> match end)
  end

  # Tags each match with {identity, n}, where n counts earlier matches with the
  # same identity in its file. Identity uses base names, so a copy listed without
  # a state still matches its state-qualified original in another file.
  defp number_occurrences(matches) do
    {tagged, _seen} =
      Enum.map_reduce(matches, %{}, fn m, seen ->
        identity = {m.competition, m.season, TeamName.base(m.home_key), TeamName.base(m.away_key)}
        n = Map.get(seen, identity, 0)
        {{{identity, n}, m}, Map.put(seen, identity, n + 1)}
      end)

    tagged
  end

  @doc "Loads every player in `fifa_data.csv` found in `dir`."
  @spec load_players(Path.t()) :: [Player.t()]
  def load_players(dir) do
    dir
    |> read_rows("fifa_data.csv")
    |> Enum.map(&to_player/1)
    |> Enum.reject(&is_nil/1)
  end

  defp read_rows(dir, file) do
    dir |> Path.join(file) |> File.read!() |> CSV.parse_maps()
  end

  defp from_brasileirao(row) do
    build(%{
      date: row["datetime"],
      home: row["home_team"],
      away: row["away_team"],
      home_state: row["home_team_state"],
      away_state: row["away_team_state"],
      home_goals: row["home_goal"],
      away_goals: row["away_goal"],
      season: row["season"],
      round: row["round"],
      competition: "brasileirao"
    })
  end

  defp from_historical(row) do
    build(%{
      date: row["Data"],
      home: row["Equipe_mandante"],
      away: row["Equipe_visitante"],
      home_state: row["Mandante_UF"],
      away_state: row["Visitante_UF"],
      home_goals: row["Gols_mandante"],
      away_goals: row["Gols_visitante"],
      season: row["Ano"],
      round: row["Rodada"],
      competition: "brasileirao"
    })
  end

  defp from_cup(row) do
    build(%{
      date: row["datetime"],
      home: row["home_team"],
      away: row["away_team"],
      home_goals: row["home_goal"],
      away_goals: row["away_goal"],
      season: row["season"],
      round: row["round"],
      competition: "copa_do_brasil"
    })
  end

  defp from_libertadores(row) do
    build(%{
      date: row["datetime"],
      home: row["home_team"],
      away: row["away_team"],
      home_goals: row["home_goal"],
      away_goals: row["away_goal"],
      season: row["season"],
      round: row["stage"],
      competition: "libertadores"
    })
  end

  defp from_br_football(row) do
    build(%{
      date: row["date"],
      home: row["home"],
      away: row["away"],
      home_goals: row["home_goal"],
      away_goals: row["away_goal"],
      season: nil,
      round: nil,
      competition: Competition.canonical(row["tournament"])
    })
  end

  defp build(attrs) do
    with {:ok, date} <- parse_date(attrs.date),
         home when is_binary(home) <- blank_to_nil(attrs.home),
         away when is_binary(away) <- blank_to_nil(attrs.away),
         home_goals when is_integer(home_goals) <- to_int(attrs.home_goals),
         away_goals when is_integer(away_goals) <- to_int(attrs.away_goals) do
      Match.new(%{
        date: date,
        competition: attrs.competition,
        season: to_int(attrs.season) || date.year,
        round: blank_to_nil(attrs.round),
        home: home,
        away: away,
        home_state: blank_to_nil(Map.get(attrs, :home_state)),
        away_state: blank_to_nil(Map.get(attrs, :away_state)),
        home_goals: home_goals,
        away_goals: away_goals
      })
    else
      _ -> nil
    end
  end

  defp to_player(row) do
    name = blank_to_nil(row["Name"])
    overall = to_int(row["Overall"])

    if name && overall do
      Player.new(%{
        name: name,
        age: to_int(row["Age"]),
        nationality: blank_to_nil(row["Nationality"]),
        overall: overall,
        potential: to_int(row["Potential"]),
        club: blank_to_nil(row["Club"]),
        position: blank_to_nil(row["Position"]),
        value: blank_to_nil(row["Value"])
      })
    end
  end

  # Accepts "2023-09-24", "2023-09-24 18:30:00" and the historical "29/03/2003".
  defp parse_date(value) when is_binary(value) do
    value = String.trim(value)

    case {Regex.run(@iso_date, value), Regex.run(@br_date, value)} do
      {[_, y, m, d], _} ->
        Date.new(String.to_integer(y), String.to_integer(m), String.to_integer(d))

      {_, [_, d, m, y]} ->
        Date.new(String.to_integer(y), String.to_integer(m), String.to_integer(d))

      _ ->
        :error
    end
  end

  defp parse_date(_), do: :error

  # Scores appear as "2", "2.0" or "2" in quotes depending on the source file.
  defp to_int(value) when is_binary(value) do
    case Float.parse(String.trim(value)) do
      {number, ""} -> trunc(number)
      _ -> nil
    end
  end

  defp to_int(_), do: nil

  defp blank_to_nil(value) when is_binary(value) do
    case String.trim(value) do
      "" -> nil
      trimmed -> trimmed
    end
  end

  defp blank_to_nil(_), do: nil
end
