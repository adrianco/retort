defmodule BrazilianSoccerMcp.Catalog do
  @moduledoc "Normalizes all supplied Kaggle files into one queryable soccer catalog."
  alias BrazilianSoccerMcp.CSV

  @match_sources [
    {"Brasileirao_Matches.csv", "Brasileirão", :brasileirao},
    {"Brazilian_Cup_Matches.csv", "Copa do Brasil", :cup},
    {"Libertadores_Matches.csv", "Libertadores", :libertadores},
    {"BR-Football-Dataset.csv", "Extended Statistics", :extended},
    {"novo_campeonato_brasileiro.csv", "Brasileirão Historical", :historical}
  ]

  defstruct matches: [], players: []

  @type match :: %{
          date: String.t() | nil,
          home: String.t(),
          away: String.t(),
          home_key: String.t(),
          away_key: String.t(),
          home_goals: integer() | nil,
          away_goals: integer() | nil,
          season: integer() | nil,
          competition: String.t(),
          round: String.t() | nil,
          stage: String.t() | nil,
          source: String.t(),
          extras: map()
        }
  @type t :: %__MODULE__{matches: [match()], players: [map()]}

  @spec load(Path.t()) :: {:ok, t()} | {:error, term()}
  def load(data_dir) do
    with {:ok, matches} <- load_matches(data_dir),
         {:ok, players} <- load_players(data_dir) do
      {:ok, %__MODULE__{matches: matches, players: players}}
    end
  end

  defp load_matches(data_dir) do
    @match_sources
    |> Enum.reduce_while({:ok, []}, fn {file, competition, kind}, {:ok, acc} ->
      case CSV.read(Path.join(data_dir, file)) do
        {:ok, rows} ->
          mapped = Enum.map(rows, &map_match(&1, kind, competition, file))
          {:cont, {:ok, mapped ++ acc}}

        {:error, reason} ->
          {:halt, {:error, {file, reason}}}
      end
    end)
  end

  defp map_match(row, :brasileirao, competition, source),
    do: from_brasileirao(row, competition, source)

  defp map_match(row, :cup, competition, source), do: from_cup(row, competition, source)

  defp map_match(row, :libertadores, competition, source),
    do: from_libertadores(row, competition, source)

  defp map_match(row, :extended, competition, source), do: from_extended(row, competition, source)

  defp map_match(row, :historical, competition, source),
    do: from_historical(row, competition, source)

  defp load_players(data_dir) do
    case CSV.read(Path.join(data_dir, "fifa_data.csv")) do
      {:ok, rows} -> {:ok, Enum.map(rows, &from_player/1)}
      error -> error
    end
  end

  defp from_brasileirao(row, competition, source),
    do:
      base(
        row,
        competition,
        source,
        row["datetime"],
        row["home_team"],
        row["away_team"],
        row["home_goal"],
        row["away_goal"],
        row["season"],
        row["round"],
        nil
      )

  defp from_cup(row, competition, source),
    do:
      base(
        row,
        competition,
        source,
        row["datetime"],
        row["home_team"],
        row["away_team"],
        row["home_goal"],
        row["away_goal"],
        row["season"],
        row["round"],
        nil
      )

  defp from_libertadores(row, competition, source),
    do:
      base(
        row,
        competition,
        source,
        row["datetime"],
        row["home_team"],
        row["away_team"],
        row["home_goal"],
        row["away_goal"],
        row["season"],
        nil,
        row["stage"]
      )

  defp from_extended(row, _competition, source),
    do:
      base(
        row,
        row["tournament"],
        source,
        row["date"],
        row["home"],
        row["away"],
        row["home_goal"],
        row["away_goal"],
        year_from(row["date"]),
        nil,
        nil
      )

  defp from_historical(row, competition, source),
    do:
      base(
        row,
        competition,
        source,
        normalize_date(row["Data"]),
        row["Equipe_mandante"],
        row["Equipe_visitante"],
        row["Gols_mandante"],
        row["Gols_visitante"],
        row["Ano"],
        row["Rodada"],
        nil
      )

  defp base(
         row,
         competition,
         source,
         date,
         home,
         away,
         home_goals,
         away_goals,
         season,
         round,
         stage
       ) do
    %{
      date: normalize_date(date),
      home: home,
      away: away,
      home_key: team_key(home),
      away_key: team_key(away),
      home_goals: integer(home_goals),
      away_goals: integer(away_goals),
      season: integer(season),
      competition: competition || "Unknown",
      round: blank_to_nil(round),
      stage: blank_to_nil(stage),
      source: source,
      extras: row
    }
  end

  defp from_player(row) do
    %{
      id: row["ID"],
      name: row["Name"],
      name_key: search_key(row["Name"]),
      nationality: row["Nationality"],
      club: row["Club"],
      club_key: search_key(row["Club"]),
      position: row["Position"],
      overall: integer(row["Overall"]),
      potential: integer(row["Potential"]),
      age: integer(row["Age"])
    }
  end

  @doc "Canonical comparison key: accent-insensitive and ignores Brazilian state suffixes."
  def team_key(name) do
    name
    |> to_string()
    |> String.replace(~r/\s*-\s*[A-Z]{2}\s*$/u, "")
    |> search_key()
  end

  def search_key(nil), do: ""

  def search_key(value),
    do:
      value
      |> to_string()
      |> String.normalize(:nfd)
      |> String.replace(~r/[\p{Mn}]/u, "")
      |> String.downcase()
      |> String.replace(~r/[^a-z0-9]+/u, " ")
      |> String.trim()

  defp normalize_date(nil), do: nil

  defp normalize_date(value) do
    value = String.trim(to_string(value))

    case Regex.run(~r/^(\d{2})\/(\d{2})\/(\d{4})$/, value) do
      [_, day, month, year] -> "#{year}-#{month}-#{day}"
      _ -> value |> String.slice(0, 10) |> blank_to_nil()
    end
  end

  defp year_from(date) do
    case normalize_date(date) do
      nil -> nil
      <<year::binary-size(4), _::binary>> -> integer(year)
      _ -> nil
    end
  end

  defp blank_to_nil(nil), do: nil

  defp blank_to_nil(value),
    do: if(String.trim(to_string(value)) == "", do: nil, else: to_string(value))

  defp integer(nil), do: nil

  defp integer(value) do
    case Float.parse(String.trim(to_string(value))) do
      {number, _} -> trunc(number)
      :error -> nil
    end
  end
end
