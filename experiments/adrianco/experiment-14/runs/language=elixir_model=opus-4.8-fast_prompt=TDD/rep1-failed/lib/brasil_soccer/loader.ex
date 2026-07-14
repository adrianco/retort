defmodule BrasilSoccer.Loader do
  @moduledoc """
  Loads the raw Kaggle CSV files and transforms each file's idiosyncratic shape
  into the unified `BrasilSoccer.Match` struct (and a player map for the FIFA
  data).

  Each source file gets its own transform function because column names,
  competitions, and date formats differ. `load_dir/1` ties them together.
  """

  alias BrasilSoccer.{CSV, Match}

  @files %{
    brasileirao: "Brasileirao_Matches.csv",
    cup: "Brazilian_Cup_Matches.csv",
    libertadores: "Libertadores_Matches.csv",
    br_football: "BR-Football-Dataset.csv",
    novo: "novo_campeonato_brasileiro.csv",
    players: "fifa_data.csv"
  }

  @doc """
  Load every CSV in `dir` and return `%{matches: [...], players: [...]}`.
  Missing files are skipped so a partial data directory still loads.
  """
  @spec load_dir(Path.t()) :: %{matches: [Match.t()], players: [map()]}
  def load_dir(dir) do
    matches =
      [:brasileirao, :cup, :libertadores, :br_football, :novo]
      |> Enum.flat_map(fn key -> rows(dir, key) |> then(&apply(__MODULE__, key, [&1])) end)

    %{matches: matches, players: players(rows(dir, :players))}
  end

  defp rows(dir, key) do
    path = Path.join(dir, @files[key])
    if File.exists?(path), do: CSV.parse_file(path), else: []
  end

  @doc "Transform Brasileirão Serie A rows."
  def brasileirao(rows) do
    Enum.map(rows, fn r ->
      Match.new(%{
        competition: "Brasileirão",
        season: to_int(r["season"]),
        round: blank_to_nil(r["round"]),
        date: parse_date(r["datetime"]),
        home_team: r["home_team"],
        away_team: r["away_team"],
        home_state: blank_to_nil(r["home_team_state"]),
        away_state: blank_to_nil(r["away_team_state"]),
        home_goal: to_int(r["home_goal"]),
        away_goal: to_int(r["away_goal"]),
        source: "Brasileirao_Matches.csv"
      })
    end)
  end

  @doc "Transform Copa do Brasil rows."
  def cup(rows) do
    Enum.map(rows, fn r ->
      Match.new(%{
        competition: "Copa do Brasil",
        season: to_int(r["season"]),
        round: blank_to_nil(r["round"]),
        date: parse_date(r["datetime"]),
        home_team: r["home_team"],
        away_team: r["away_team"],
        home_goal: to_int(r["home_goal"]),
        away_goal: to_int(r["away_goal"]),
        source: "Brazilian_Cup_Matches.csv"
      })
    end)
  end

  @doc "Transform Copa Libertadores rows."
  def libertadores(rows) do
    Enum.map(rows, fn r ->
      Match.new(%{
        competition: "Libertadores",
        season: to_int(r["season"]),
        stage: blank_to_nil(r["stage"]),
        date: parse_date(r["datetime"]),
        home_team: r["home_team"],
        away_team: r["away_team"],
        home_goal: to_int(r["home_goal"]),
        away_goal: to_int(r["away_goal"]),
        source: "Libertadores_Matches.csv"
      })
    end)
  end

  @doc "Transform the extended BR-Football statistics rows."
  def br_football(rows) do
    Enum.map(rows, fn r ->
      Match.new(%{
        competition: blank_to_nil(r["tournament"]) || "Brazilian Football",
        date: parse_date(r["date"]),
        season: season_from_date(r["date"]),
        home_team: r["home"],
        away_team: r["away"],
        home_goal: to_int(r["home_goal"]),
        away_goal: to_int(r["away_goal"]),
        source: "BR-Football-Dataset.csv"
      })
    end)
  end

  @doc "Transform the historical Brasileirão (Portuguese columns) rows."
  def novo(rows) do
    Enum.map(rows, fn r ->
      Match.new(%{
        competition: "Brasileirão",
        season: to_int(r["Ano"]),
        round: blank_to_nil(r["Rodada"]),
        date: parse_date(r["Data"]),
        home_team: r["Equipe_mandante"],
        away_team: r["Equipe_visitante"],
        home_state: blank_to_nil(r["Mandante_UF"]),
        away_state: blank_to_nil(r["Visitante_UF"]),
        home_goal: to_int(r["Gols_mandante"]),
        away_goal: to_int(r["Gols_visitante"]),
        source: "novo_campeonato_brasileiro.csv"
      })
    end)
  end

  @doc "Transform FIFA player rows into player maps."
  def players(rows) do
    Enum.map(rows, fn r ->
      %{
        id: to_int(r["ID"]),
        name: blank_to_nil(r["Name"]),
        age: to_int(r["Age"]),
        nationality: blank_to_nil(r["Nationality"]),
        overall: to_int(r["Overall"]),
        potential: to_int(r["Potential"]),
        club: blank_to_nil(r["Club"]),
        position: blank_to_nil(r["Position"]),
        jersey_number: to_int(r["Jersey Number"]),
        height: blank_to_nil(r["Height"]),
        weight: blank_to_nil(r["Weight"]),
        preferred_foot: blank_to_nil(r["Preferred Foot"])
      }
    end)
  end

  @doc """
  Parse the date formats used across the datasets: `YYYY-MM-DD[ HH:MM:SS]` and
  Brazilian `DD/MM/YYYY`. Returns a `Date` or `nil`.
  """
  @spec parse_date(String.t() | nil) :: Date.t() | nil
  def parse_date(nil), do: nil

  def parse_date(value) when is_binary(value) do
    value = value |> String.split() |> List.first() |> to_string()

    cond do
      value == "" -> nil
      String.contains?(value, "/") -> parse_br_date(value)
      true -> parse_iso_date(value)
    end
  end

  defp parse_br_date(value) do
    with [d, m, y] <- String.split(value, "/"),
         {day, ""} <- Integer.parse(d),
         {month, ""} <- Integer.parse(m),
         {year, ""} <- Integer.parse(y),
         {:ok, date} <- Date.new(year, month, day) do
      date
    else
      _ -> nil
    end
  end

  defp parse_iso_date(value) do
    case Date.from_iso8601(value) do
      {:ok, date} -> date
      _ -> nil
    end
  end

  defp season_from_date(value) do
    case parse_date(value) do
      %Date{year: year} -> year
      _ -> nil
    end
  end

  @doc """
  Coerce a string to an integer, tolerating float strings (`"2.0"`) and blanks.
  """
  @spec to_int(String.t() | nil) :: integer() | nil
  def to_int(nil), do: nil

  def to_int(value) when is_binary(value) do
    case Integer.parse(String.trim(value)) do
      {n, ""} -> n
      {n, "." <> _} -> n
      _ -> nil
    end
  end

  defp blank_to_nil(nil), do: nil

  defp blank_to_nil(value) do
    case String.trim(value) do
      "" -> nil
      trimmed -> trimmed
    end
  end
end
