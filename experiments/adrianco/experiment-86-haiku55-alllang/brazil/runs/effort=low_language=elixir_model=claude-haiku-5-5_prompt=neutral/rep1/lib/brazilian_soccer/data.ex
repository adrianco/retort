defmodule BrazilianSoccer.Data do
  @moduledoc """
  Loads the Kaggle CSV datasets from a directory into memory.

  All five match files are merged into one list of `BrazilianSoccer.Match`.
  The files overlap (the 2003-2019 historical file and the Brasileirão file
  both cover 2012-2019; BR-Football also contains Brasileirão rows), so a match
  is kept once, taking the first occurrence in load order (see `duplicate_key`
  below). Rows without a parseable date, teams or goals are skipped.

  The FIFA file is loaded into `BrazilianSoccer.Player` structs.
  """

  alias BrazilianSoccer.{CSV, Dates, Match, Normalize, Player}

  @serie_a "Brasileirão Série A"
  @serie_b "Brasileirão Série B"
  @serie_c "Brasileirão Série C"
  @copa_do_brasil "Copa do Brasil"
  @libertadores "Copa Libertadores"

  @br_football_tournaments %{
    "Serie A" => @serie_a,
    "Serie B" => @serie_b,
    "Serie C" => @serie_c,
    "Copa do Brasil" => @copa_do_brasil
  }

  defstruct matches: [], players: []

  @type t :: %__MODULE__{matches: [Match.t()], players: [Player.t()]}

  @doc "Loads every dataset found in `dir`. Raises if a file is missing."
  @spec load(Path.t()) :: t()
  def load(dir) do
    matches =
      [
        brasileirao(dir),
        cup(dir),
        libertadores(dir),
        historical(dir),
        br_football(dir)
      ]
      |> Enum.concat()
      |> Enum.reject(&incomplete?/1)
      |> Enum.uniq_by(&duplicate_key/1)

    %__MODULE__{matches: matches, players: players(dir)}
  end

  defp brasileirao(dir) do
    file = "Brasileirao_Matches.csv"

    for row <- read(dir, file) do
      match(%{
        date: row["datetime"],
        competition: @serie_a,
        stage: round_label(row["round"]),
        home: row["home_team"],
        away: row["away_team"],
        home_goals: row["home_goal"],
        away_goals: row["away_goal"],
        source: file
      })
    end
  end

  defp cup(dir) do
    file = "Brazilian_Cup_Matches.csv"

    for row <- read(dir, file) do
      match(%{
        date: row["datetime"],
        competition: @copa_do_brasil,
        stage: round_label(row["round"]),
        home: row["home_team"],
        away: row["away_team"],
        home_goals: row["home_goal"],
        away_goals: row["away_goal"],
        source: file
      })
    end
  end

  defp libertadores(dir) do
    file = "Libertadores_Matches.csv"

    for row <- read(dir, file) do
      match(%{
        date: row["datetime"],
        competition: @libertadores,
        stage: blank_to_nil(row["stage"]),
        home: row["home_team"],
        away: row["away_team"],
        home_goals: row["home_goal"],
        away_goals: row["away_goal"],
        source: file
      })
    end
  end

  defp historical(dir) do
    file = "novo_campeonato_brasileiro.csv"

    for row <- read(dir, file) do
      match(%{
        date: row["Data"],
        competition: @serie_a,
        stage: round_label(row["Rodada"]),
        home: row["Equipe_mandante"],
        away: row["Equipe_visitante"],
        home_goals: row["Gols_mandante"],
        away_goals: row["Gols_visitante"],
        source: file
      })
    end
  end

  defp br_football(dir) do
    file = "BR-Football-Dataset.csv"

    for row <- read(dir, file) do
      match(%{
        date: row["date"],
        competition: Map.get(@br_football_tournaments, row["tournament"], row["tournament"]),
        stage: nil,
        home: row["home"],
        away: row["away"],
        home_goals: row["home_goal"],
        away_goals: row["away_goal"],
        source: file
      })
    end
  end

  defp players(dir) do
    for row <- read(dir, "fifa_data.csv") do
      %Player{
        id: Normalize.integer(row["ID"]),
        name: row["Name"],
        age: Normalize.integer(row["Age"]),
        nationality: row["Nationality"],
        club: row["Club"],
        position: row["Position"],
        overall: Normalize.integer(row["Overall"]) || 0,
        potential: Normalize.integer(row["Potential"]),
        jersey_number: Normalize.integer(row["Jersey Number"]),
        value: row["Value"],
        wage: row["Wage"]
      }
    end
  end

  # Converts raw cell text to a match. Unparseable cells become nil and the
  # row is dropped later by `incomplete?/1`.
  defp match(raw) do
    Match.new(%{
      raw
      | date: parse_date(raw.date),
        home_goals: Normalize.integer(raw.home_goals),
        away_goals: Normalize.integer(raw.away_goals)
    })
  end

  # Sources disagree on dates by a day and occasionally on scores, so the key
  # leans on the season and orientation. In a league a pair meets at most once
  # per orientation per season, so the score is not needed. Cups and
  # Libertadores can repeat a pairing in one season (two legs, reversed
  # orientation), so the score is included there to keep the legs apart.
  defp duplicate_key(%Match{competition: "Brasileirão" <> _} = m) do
    {m.competition, m.date.year, m.home_key, m.away_key}
  end

  defp duplicate_key(%Match{} = m) do
    {m.competition, m.date.year, m.home_key, m.away_key, m.home_goals, m.away_goals}
  end

  defp incomplete?(%Match{} = m) do
    is_nil(m.date) or is_nil(m.home_goals) or is_nil(m.away_goals) or
      m.home_key == "" or m.away_key == ""
  end

  defp parse_date(text) do
    case Dates.parse(text) do
      {:ok, date} -> date
      :error -> nil
    end
  end

  # "22" -> "Round 22"; non-numeric stages such as "final" are kept as written.
  defp round_label(value) do
    case blank_to_nil(value) do
      nil -> nil
      text -> if Regex.match?(~r/^\d+$/, text), do: "Round #{text}", else: text
    end
  end

  defp blank_to_nil(value) do
    case value && String.trim(value) do
      nil -> nil
      "" -> nil
      text -> text
    end
  end

  defp read(dir, file) do
    dir
    |> Path.join(file)
    |> File.read!()
    |> CSV.parse_with_headers()
  end
end
