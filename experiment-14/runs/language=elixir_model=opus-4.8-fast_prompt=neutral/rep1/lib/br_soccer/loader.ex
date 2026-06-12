defmodule BrSoccer.Loader do
  @moduledoc """
  Loads the six Kaggle CSVs into normalised `BrSoccer.Match` and
  `BrSoccer.Player` structs.

  Each file has its own column layout, date format and naming convention; this
  module is the single place that knows about those quirks. Team names are run
  through `BrSoccer.TeamName` so downstream code can match clubs consistently.
  """

  alias BrSoccer.{CSV, Match, Player, TeamName}

  @default_dir "data/kaggle"

  @doc "Directory the CSVs live in (overridable via the `:br_soccer, :data_dir` config)."
  def data_dir do
    Application.get_env(:br_soccer, :data_dir, @default_dir)
  end

  @doc "Load everything, returning `%{matches: [...], players: [...]}`."
  def load_all(dir \\ data_dir()) do
    %{
      matches: load_matches(dir),
      players: load_players(dir)
    }
  end

  # When more than one file covers the same fixture (the Brasileirão appears in
  # three files, Copa do Brasil in two), keep the record from the most
  # authoritative source. Lower index = higher priority.
  @source_priority [:brasileirao_csv, :novo, :br_football, :cup_csv, :libertadores_csv]

  # Competitions whose fixtures are duplicated across sources.
  @deduped_competitions [:brasileirao, :copa_do_brasil]

  @doc "Load and concatenate all match files, de-duplicating overlapping fixtures."
  def load_matches(dir \\ data_dir()) do
    [
      load_brasileirao(dir),
      load_cup(dir),
      load_libertadores(dir),
      load_br_football(dir),
      load_novo(dir)
    ]
    |> List.flatten()
    |> dedup()
  end

  # Collapse the same fixture (competition+season+home+away) reported by several
  # sources to a single record, preferring the highest-priority source. Records
  # without a season, or from competitions with a single source, pass through.
  defp dedup(matches) do
    {candidates, others} =
      Enum.split_with(matches, &(&1.competition in @deduped_competitions and &1.season != nil))

    deduped =
      candidates
      |> Enum.group_by(&{&1.competition, &1.season, &1.home_key, &1.away_key})
      |> Enum.map(fn {_key, group} -> Enum.min_by(group, &source_rank(&1.source)) end)

    others ++ deduped
  end

  defp source_rank(source) do
    Enum.find_index(@source_priority, &(&1 == source)) || length(@source_priority)
  end

  # ---- Brasileirao_Matches.csv ----
  defp load_brasileirao(dir) do
    Path.join(dir, "Brasileirao_Matches.csv")
    |> CSV.parse_file()
    |> Enum.map(fn r ->
      new_match(
        competition: :brasileirao,
        source: :brasileirao_csv,
        season: to_int(r["season"]),
        date: parse_date(r["datetime"]),
        round: to_int(r["round"]),
        home_raw: r["home_team"],
        away_raw: r["away_team"],
        home_goal: to_int(r["home_goal"]),
        away_goal: to_int(r["away_goal"]),
        home_state: blank_to_nil(r["home_team_state"]),
        away_state: blank_to_nil(r["away_team_state"])
      )
    end)
  end

  # ---- Brazilian_Cup_Matches.csv ----
  defp load_cup(dir) do
    Path.join(dir, "Brazilian_Cup_Matches.csv")
    |> CSV.parse_file()
    |> Enum.map(fn r ->
      new_match(
        competition: :copa_do_brasil,
        source: :cup_csv,
        season: to_int(r["season"]),
        date: parse_date(r["datetime"]),
        stage: blank_to_nil(r["round"]),
        home_raw: r["home_team"],
        away_raw: r["away_team"],
        home_goal: to_int(r["home_goal"]),
        away_goal: to_int(r["away_goal"])
      )
    end)
  end

  # ---- Libertadores_Matches.csv ----
  defp load_libertadores(dir) do
    Path.join(dir, "Libertadores_Matches.csv")
    |> CSV.parse_file()
    |> Enum.map(fn r ->
      new_match(
        competition: :libertadores,
        source: :libertadores_csv,
        season: to_int(r["season"]),
        date: parse_date(r["datetime"]),
        stage: blank_to_nil(r["stage"]),
        home_raw: r["home_team"],
        away_raw: r["away_team"],
        home_goal: to_int(r["home_goal"]),
        away_goal: to_int(r["away_goal"])
      )
    end)
  end

  # ---- BR-Football-Dataset.csv (note: column order is home, home_goal, away_goal, away) ----
  defp load_br_football(dir) do
    Path.join(dir, "BR-Football-Dataset.csv")
    |> CSV.parse_file()
    |> Enum.map(fn r ->
      date = parse_date(r["date"])

      new_match(
        competition: tournament_to_competition(r["tournament"]),
        source: :br_football,
        season: date && date.year,
        date: date,
        home_raw: r["home"],
        away_raw: r["away"],
        home_goal: to_int(r["home_goal"]),
        away_goal: to_int(r["away_goal"]),
        stats: %{
          home_corner: to_int(r["home_corner"]),
          away_corner: to_int(r["away_corner"]),
          home_shots: to_int(r["home_shots"]),
          away_shots: to_int(r["away_shots"]),
          home_attack: to_int(r["home_attack"]),
          away_attack: to_int(r["away_attack"]),
          total_corners: to_int(r["total_corners"])
        }
      )
    end)
  end

  # ---- novo_campeonato_brasileiro.csv (Portuguese columns, DD/MM/YYYY dates) ----
  defp load_novo(dir) do
    Path.join(dir, "novo_campeonato_brasileiro.csv")
    |> CSV.parse_file()
    |> Enum.map(fn r ->
      new_match(
        competition: :brasileirao,
        source: :novo,
        season: to_int(r["Ano"]),
        date: parse_date(r["Data"]),
        round: to_int(r["Rodada"]),
        home_raw: r["Equipe_mandante"],
        away_raw: r["Equipe_visitante"],
        home_goal: to_int(r["Gols_mandante"]),
        away_goal: to_int(r["Gols_visitante"]),
        home_state: blank_to_nil(r["Mandante_UF"]),
        away_state: blank_to_nil(r["Visitante_UF"]),
        arena: blank_to_nil(r["Arena"])
      )
    end)
  end

  # ---- fifa_data.csv ----
  @doc "Load FIFA player records."
  def load_players(dir \\ data_dir()) do
    Path.join(dir, "fifa_data.csv")
    |> CSV.parse_file()
    |> Enum.map(fn r ->
      club = blank_to_nil(r["Club"])

      %Player{
        id: to_int(r["ID"]),
        name: r["Name"],
        age: to_int(r["Age"]),
        nationality: r["Nationality"],
        overall: to_int(r["Overall"]),
        potential: to_int(r["Potential"]),
        club: club,
        club_key: club && TeamName.key(club),
        position: blank_to_nil(r["Position"]),
        jersey: to_int(r["Jersey Number"]),
        height: blank_to_nil(r["Height"]),
        weight: blank_to_nil(r["Weight"]),
        value: blank_to_nil(r["Value"]),
        wage: blank_to_nil(r["Wage"]),
        preferred_foot: blank_to_nil(r["Preferred Foot"])
      }
    end)
  end

  # ---- helpers ----

  defp new_match(opts) do
    home_raw = Keyword.fetch!(opts, :home_raw)
    away_raw = Keyword.fetch!(opts, :away_raw)

    %Match{
      competition: Keyword.fetch!(opts, :competition),
      source: Keyword.fetch!(opts, :source),
      season: Keyword.get(opts, :season),
      date: Keyword.get(opts, :date),
      round: Keyword.get(opts, :round),
      stage: Keyword.get(opts, :stage),
      home: TeamName.display(home_raw),
      away: TeamName.display(away_raw),
      home_key: TeamName.key(home_raw),
      away_key: TeamName.key(away_raw),
      home_goal: Keyword.get(opts, :home_goal),
      away_goal: Keyword.get(opts, :away_goal),
      home_state: Keyword.get(opts, :home_state),
      away_state: Keyword.get(opts, :away_state),
      arena: Keyword.get(opts, :arena),
      stats: Keyword.get(opts, :stats, %{})
    }
  end

  defp tournament_to_competition(t) do
    case String.downcase(to_string(t)) do
      "serie a" -> :brasileirao
      "serie b" -> :serie_b
      "serie c" -> :serie_c
      "copa do brasil" -> :copa_do_brasil
      _ -> :other
    end
  end

  @doc false
  def to_int(nil), do: nil

  def to_int(v) when is_binary(v) do
    s = String.trim(v)

    cond do
      s == "" -> nil
      true ->
        # Accept "2", "2.0", " 3 ". Anything non-numeric -> nil.
        case Integer.parse(s) do
          {n, ""} -> n
          {n, "." <> rest} -> if rest =~ ~r/^0*$/, do: n, else: nil
          _ -> nil
        end
    end
  end

  def to_int(v) when is_integer(v), do: v
  def to_int(_), do: nil

  defp blank_to_nil(nil), do: nil
  defp blank_to_nil(v) do
    case String.trim(to_string(v)) do
      "" -> nil
      s -> s
    end
  end

  @doc """
  Parse the several date formats found across the datasets:

    * `2012-05-19 18:30:00` and `2023-09-24` (ISO, optional time)
    * `29/03/2003` (Brazilian DD/MM/YYYY)
  """
  def parse_date(nil), do: nil

  def parse_date(s) when is_binary(s) do
    s = String.trim(s)

    cond do
      s == "" -> nil
      Regex.match?(~r/^\d{4}-\d{2}-\d{2}/, s) -> iso_date(s)
      Regex.match?(~r"^\d{1,2}/\d{1,2}/\d{4}", s) -> br_date(s)
      true -> nil
    end
  end

  defp iso_date(s) do
    <<y::binary-4, "-", m::binary-2, "-", d::binary-2, _::binary>> = s
    build_date(y, m, d)
  end

  defp br_date(s) do
    [d, m, y | _] = String.split(s, ["/", " "])
    build_date(y, m, d)
  end

  defp build_date(y, m, d) do
    with {yy, _} <- Integer.parse(y),
         {mm, _} <- Integer.parse(m),
         {dd, _} <- Integer.parse(d),
         {:ok, date} <- Date.new(yy, mm, dd) do
      date
    else
      _ -> nil
    end
  end
end
