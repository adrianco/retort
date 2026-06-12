defmodule BrazilianSoccerMcp.DataStore do
  @moduledoc """
  Loads all six CSV datasets into ETS tables on startup and exposes
  query functions over those tables.
  """
  use GenServer

  require Logger

  alias BrazilianSoccerMcp.TeamNormalizer

  NimbleCSV.define(BrazilianSoccerMcp.CSV, separator: ",", escape: "\"")

  @tables [
    :brasileirao,
    :cup,
    :libertadores,
    :br_football,
    :historico,
    :fifa
  ]

  # ---------- public API ----------

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @doc "All matches from a given dataset. dataset ∈ :brasileirao | :cup | :libertadores | :br_football | :historico"
  def all_matches(dataset), do: ets_all(dataset)

  @doc "All players from FIFA dataset"
  def all_players, do: ets_all(:fifa)

  # ---------- GenServer callbacks ----------

  @impl true
  def init(_opts) do
    for t <- @tables do
      :ets.new(t, [:named_table, :public, :bag, read_concurrency: true])
    end

    load_all()
    Logger.info("DataStore: all CSV files loaded")
    {:ok, %{}}
  end

  # ---------- loading ----------

  defp load_all do
    load_brasileirao()
    load_cup()
    load_libertadores()
    load_br_football()
    load_historico()
    load_fifa()
  end

  defp data_path(file), do: Path.join(data_dir(), file)

  defp data_dir do
    Application.get_env(:brazilian_soccer_mcp, :data_dir, "data")
    |> Path.join("kaggle")
  end

  # 1. Brasileirao_Matches.csv
  # datetime,home_team,home_team_state,away_team,away_team_state,home_goal,away_goal,season,round
  defp load_brasileirao do
    parse_csv(data_path("Brasileirao_Matches.csv"), fn
      [datetime, home, _hs, away, _as, hg, ag, season, round] ->
        :ets.insert(:brasileirao, {
          normalize(home),
          normalize(away),
          parse_date(datetime),
          safe_int(hg),
          safe_int(ag),
          safe_int(season),
          safe_int(round),
          "Brasileirao"
        })

      _ ->
        :ok
    end)
  end

  # 2. Brazilian_Cup_Matches.csv
  # round,datetime,home_team,away_team,home_goal,away_goal,season
  defp load_cup do
    parse_csv(data_path("Brazilian_Cup_Matches.csv"), fn
      [round, datetime, home, away, hg, ag, season] ->
        :ets.insert(:cup, {
          normalize(home),
          normalize(away),
          parse_date(datetime),
          safe_int(hg),
          safe_int(ag),
          safe_int(season),
          round,
          "Copa do Brasil"
        })

      _ ->
        :ok
    end)
  end

  # 3. Libertadores_Matches.csv
  # datetime,home_team,away_team,home_goal,away_goal,season,stage
  defp load_libertadores do
    parse_csv(data_path("Libertadores_Matches.csv"), fn
      [datetime, home, away, hg, ag, season, stage] ->
        :ets.insert(:libertadores, {
          normalize(home),
          normalize(away),
          parse_date(datetime),
          safe_int(hg),
          safe_int(ag),
          safe_int(season),
          stage,
          "Libertadores"
        })

      _ ->
        :ok
    end)
  end

  # 4. BR-Football-Dataset.csv
  # tournament,home,home_goal,away_goal,away,...,date,...
  defp load_br_football do
    parse_csv(data_path("BR-Football-Dataset.csv"), fn
      [tournament, home, hg, ag, away, _hc, _ac, _ha, _aa, _hs, _as, _time, date | _rest] ->
        :ets.insert(:br_football, {
          normalize(home),
          normalize(away),
          parse_date(date),
          safe_float_to_int(hg),
          safe_float_to_int(ag),
          tournament
        })

      _ ->
        :ok
    end)
  end

  # 5. novo_campeonato_brasileiro.csv
  # ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS
  defp load_historico do
    parse_csv(data_path("novo_campeonato_brasileiro.csv"), fn
      [_id, data, ano, rodada, home, away, hg, ag, _huf, _auf, vencedor | _rest] ->
        :ets.insert(:historico, {
          normalize(home),
          normalize(away),
          parse_date(data),
          safe_int(hg),
          safe_int(ag),
          safe_int(ano),
          safe_int(rodada),
          vencedor,
          "Brasileirao"
        })

      _ ->
        :ok
    end)
  end

  # 6. fifa_data.csv — skip BOM, columns include Name, Age, Nationality, Overall, Club, Position, ...
  # The first column is an empty index col (or BOM), then ID, Name, Age, Photo, Nationality, Flag,
  # Overall, Potential, Club, Club Logo, Value, Wage, Special, Preferred Foot, International Reputation,
  # Weak Foot, Skill Moves, Work Rate, Body Type, Real Face, Position, Jersey Num, ...
  defp load_fifa do
    parse_csv(data_path("fifa_data.csv"), fn
      [_idx, _id, name, age, _photo, nationality, _flag, overall, potential, club | _rest] ->
        :ets.insert(:fifa, {
          name,
          safe_int(age),
          nationality,
          safe_int(overall),
          safe_int(potential),
          club
        })

      _ ->
        :ok
    end)
  end

  # ---------- query helpers (called by tools) ----------

  def query_matches(filters) do
    datasets = resolve_datasets(filters[:competition])

    datasets
    |> Enum.flat_map(&query_dataset(&1, filters))
    |> Enum.uniq()
  end

  defp resolve_datasets(nil), do: @tables -- [:fifa]

  defp resolve_datasets(comp) do
    comp_down = String.downcase(comp)

    cond do
      String.contains?(comp_down, "brasileir") -> [:brasileirao, :historico]
      String.contains?(comp_down, "copa do brasil") or String.contains?(comp_down, "cup") -> [:cup]
      String.contains?(comp_down, "libertad") -> [:libertadores]
      String.contains?(comp_down, "br-football") or String.contains?(comp_down, "extended") -> [:br_football]
      true -> @tables -- [:fifa]
    end
  end

  defp query_dataset(table, filters) when table in [:brasileirao] do
    :ets.tab2list(table)
    |> Enum.filter(&match_filter_brasileirao(&1, filters))
    |> Enum.map(fn {home, away, date, hg, ag, season, round, comp} ->
      %{home: home, away: away, date: date, home_goal: hg, away_goal: ag,
        season: season, round: round, competition: comp}
    end)
  end

  defp query_dataset(table, filters) when table in [:cup] do
    :ets.tab2list(table)
    |> Enum.filter(&match_filter_cup(&1, filters))
    |> Enum.map(fn {home, away, date, hg, ag, season, round, comp} ->
      %{home: home, away: away, date: date, home_goal: hg, away_goal: ag,
        season: season, round: round, competition: comp}
    end)
  end

  defp query_dataset(table, filters) when table in [:libertadores] do
    :ets.tab2list(table)
    |> Enum.filter(&match_filter_libertadores(&1, filters))
    |> Enum.map(fn {home, away, date, hg, ag, season, stage, comp} ->
      %{home: home, away: away, date: date, home_goal: hg, away_goal: ag,
        season: season, round: stage, competition: comp}
    end)
  end

  defp query_dataset(table, filters) when table in [:br_football] do
    :ets.tab2list(table)
    |> Enum.filter(&match_filter_br_football(&1, filters))
    |> Enum.map(fn {home, away, date, hg, ag, tournament} ->
      %{home: home, away: away, date: date, home_goal: hg, away_goal: ag,
        season: extract_year(date), round: nil, competition: tournament}
    end)
  end

  defp query_dataset(table, filters) when table in [:historico] do
    :ets.tab2list(table)
    |> Enum.filter(&match_filter_historico(&1, filters))
    |> Enum.map(fn {home, away, date, hg, ag, season, round, _vencedor, comp} ->
      %{home: home, away: away, date: date, home_goal: hg, away_goal: ag,
        season: season, round: round, competition: comp}
    end)
  end

  defp query_dataset(_table, _filters), do: []

  defp team_matches?(_name, nil), do: true
  defp team_matches?(name, query), do: TeamNormalizer.matches?(name, query)

  defp season_matches?(_season, nil), do: true
  defp season_matches?(season, s), do: season == s

  defp match_filter_brasileirao({home, away, _date, _hg, _ag, season, _round, _comp}, filters) do
    team1 = filters[:team1]
    team2 = filters[:team2]
    season_filter = filters[:season]

    season_matches?(season, season_filter) and
      teams_match?(home, away, team1, team2)
  end

  defp match_filter_cup({home, away, _date, _hg, _ag, season, _round, _comp}, filters) do
    team1 = filters[:team1]
    team2 = filters[:team2]
    season_filter = filters[:season]

    season_matches?(season, season_filter) and
      teams_match?(home, away, team1, team2)
  end

  defp match_filter_libertadores({home, away, _date, _hg, _ag, season, _stage, _comp}, filters) do
    team1 = filters[:team1]
    team2 = filters[:team2]
    season_filter = filters[:season]

    season_matches?(season, season_filter) and
      teams_match?(home, away, team1, team2)
  end

  defp match_filter_br_football({home, away, _date, _hg, _ag, _tournament}, filters) do
    team1 = filters[:team1]
    team2 = filters[:team2]
    teams_match?(home, away, team1, team2)
  end

  defp match_filter_historico({home, away, _date, _hg, _ag, season, _round, _v, _comp}, filters) do
    team1 = filters[:team1]
    team2 = filters[:team2]
    season_filter = filters[:season]

    season_matches?(season, season_filter) and
      teams_match?(home, away, team1, team2)
  end

  defp teams_match?(_home, _away, nil, nil), do: true

  defp teams_match?(home, away, team1, nil) do
    team_matches?(home, team1) or team_matches?(away, team1)
  end

  defp teams_match?(home, away, team1, team2) do
    (team_matches?(home, team1) and team_matches?(away, team2)) or
      (team_matches?(home, team2) and team_matches?(away, team1))
  end

  def query_players(filters) do
    :ets.tab2list(:fifa)
    |> Enum.filter(fn {name, _age, nationality, _overall, _potential, club} ->
      name_match?(name, filters[:name]) and
        nationality_match?(nationality, filters[:nationality]) and
        club_match?(club, filters[:club])
    end)
    |> Enum.map(fn {name, age, nationality, overall, potential, club} ->
      %{name: name, age: age, nationality: nationality, overall: overall,
        potential: potential, club: club}
    end)
  end

  defp name_match?(_name, nil), do: true

  defp name_match?(name, query) do
    String.contains?(String.downcase(name), String.downcase(query))
  end

  defp nationality_match?(_nat, nil), do: true

  defp nationality_match?(nationality, query) do
    String.contains?(String.downcase(nationality), String.downcase(query)) or
      String.contains?(String.downcase(query), String.downcase(nationality))
  end

  defp club_match?(_club, nil), do: true

  defp club_match?(club, query) do
    club_down = String.downcase(club)
    query_down = String.downcase(query)
    String.contains?(club_down, query_down) or
      TeamNormalizer.matches?(club, query)
  end

  # ---------- private helpers ----------

  defp ets_all(table) do
    :ets.tab2list(table)
  end

  defp parse_csv(path, row_fn) do
    path
    |> File.stream!()
    |> BrazilianSoccerMcp.CSV.parse_stream(skip_headers: true)
    |> Stream.each(fn row ->
      try do
        row_fn.(row)
      rescue
        _ -> :ok
      end
    end)
    |> Stream.run()
  rescue
    e ->
      Logger.warning("Failed to load #{path}: #{inspect(e)}")
  end

  defp normalize(name), do: TeamNormalizer.normalize(name)

  defp safe_int(val) when is_integer(val), do: val

  defp safe_int(val) when is_binary(val) do
    val = String.trim(val)
    case Integer.parse(val) do
      {i, _} -> i
      :error -> nil
    end
  end

  defp safe_int(_), do: nil

  defp safe_float_to_int(val) when is_binary(val) do
    val = String.trim(val)
    case Float.parse(val) do
      {f, _} -> round(f)
      :error ->
        case Integer.parse(val) do
          {i, _} -> i
          :error -> nil
        end
    end
  end

  defp safe_float_to_int(val) when is_float(val), do: round(val)
  defp safe_float_to_int(val) when is_integer(val), do: val
  defp safe_float_to_int(_), do: nil

  defp parse_date(nil), do: nil
  defp parse_date(""), do: nil

  defp parse_date(str) when is_binary(str) do
    str = String.trim(str)

    cond do
      # ISO with time: "2012-05-19 18:30:00"
      Regex.match?(~r/^\d{4}-\d{2}-\d{2}/, str) ->
        str |> String.slice(0, 10)

      # Brazilian format: "29/03/2003"
      Regex.match?(~r/^\d{2}\/\d{2}\/\d{4}/, str) ->
        [d, m, y] = String.split(str, "/")
        "#{y}-#{m}-#{d}"

      true ->
        str
    end
  end

  defp extract_year(nil), do: nil

  defp extract_year(date) when is_binary(date) do
    case Regex.run(~r/^(\d{4})/, date) do
      [_, y] -> safe_int(y)
      _ -> nil
    end
  end
end
