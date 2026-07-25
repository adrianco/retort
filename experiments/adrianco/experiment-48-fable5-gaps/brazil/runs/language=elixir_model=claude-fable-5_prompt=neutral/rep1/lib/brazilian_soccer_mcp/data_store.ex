defmodule BrazilianSoccerMcp.DataStore do
  @moduledoc """
  Loads all six CSV files into memory (via `:persistent_term`) once, building:

    * `matches` - a deduplicated list of `Match` structs across all match files.
      Several files cover the same games (e.g. Brasileirão 2012-2019 appears in
      `Brasileirao_Matches.csv`, `novo_campeonato_brasileiro.csv`, and
      `BR-Football-Dataset.csv`), so records are deduplicated on
      `{date, home_key, away_key}` with a fixed source-priority order; extra
      statistics (corners, shots, stadium) from lower-priority duplicates are
      merged into the surviving record.
    * `players` - `Player` structs from the FIFA dataset.
    * `teams`   - a registry of canonical team keys with display names.
  """

  alias BrazilianSoccerMcp.{CSV, Match, Player, TeamNames}

  @pt_key {__MODULE__, :data}

  def default_data_dir do
    Application.get_env(:brazilian_soccer_mcp, :data_dir) ||
      Path.join(File.cwd!(), "data/kaggle")
  end

  def loaded?, do: :persistent_term.get(@pt_key, nil) != nil

  def ensure_loaded!(dir \\ nil) do
    if not loaded?(), do: load!(dir || default_data_dir())
    :ok
  end

  def load!(dir) do
    # Priority order: richer/authoritative sources first; later duplicates
    # only contribute their extras.
    matches =
      dedupe(
        load_serie_a(Path.join(dir, "Brasileirao_Matches.csv")) ++
          load_historical(Path.join(dir, "novo_campeonato_brasileiro.csv")) ++
          load_copa(Path.join(dir, "Brazilian_Cup_Matches.csv")) ++
          load_libertadores(Path.join(dir, "Libertadores_Matches.csv")) ++
          load_extended(Path.join(dir, "BR-Football-Dataset.csv"))
      )

    players = load_players(Path.join(dir, "fifa_data.csv"))
    teams = build_registry(matches)

    :persistent_term.put(@pt_key, %{matches: matches, players: players, teams: teams})
    :ok
  end

  def matches, do: data().matches
  def players, do: data().players
  def teams, do: data().teams

  @doc "Display name for a canonical team key (state suffix added when ambiguous)."
  def display(key), do: get_in(data().teams, [key, :display]) || key

  defp data do
    :persistent_term.get(@pt_key, nil) ||
      raise "data not loaded; call BrazilianSoccerMcp.DataStore.ensure_loaded!/0 first"
  end

  # -- loaders ---------------------------------------------------------------

  defp load_serie_a(path) do
    for row <- CSV.parse_file_to_maps(path),
        date = parse_date(row["datetime"]),
        date != nil do
      home = TeamNames.normalize(row["home_team"], row["home_team_state"])
      away = TeamNames.normalize(row["away_team"], row["away_team_state"])

      %Match{
        source: :serie_a,
        competition: :brasileirao,
        date: date,
        time: parse_time(row["datetime"]),
        season: parse_int(row["season"]),
        round: row["round"],
        home: home.display,
        away: away.display,
        home_key: home.key,
        away_key: away.key,
        home_goal: parse_int(row["home_goal"]),
        away_goal: parse_int(row["away_goal"])
      }
    end
  end

  defp load_historical(path) do
    for row <- CSV.parse_file_to_maps(path),
        date = parse_date(row["Data"]),
        date != nil do
      home =
        TeamNames.normalize(
          row["Equipe_mandante"],
          fix_uf(row["Equipe_mandante"], row["Mandante_UF"])
        )

      away =
        TeamNames.normalize(
          row["Equipe_visitante"],
          fix_uf(row["Equipe_visitante"], row["Visitante_UF"])
        )

      %Match{
        source: :historical,
        competition: :brasileirao,
        date: date,
        season: parse_int(row["Ano"]),
        round: row["Rodada"],
        home: home.display,
        away: away.display,
        home_key: home.key,
        away_key: away.key,
        home_goal: parse_int(row["Gols_mandante"]),
        away_goal: parse_int(row["Gols_visitante"]),
        extras: drop_blank(%{"stadium" => row["Arena"]})
      }
    end
  end

  # Data error in novo_campeonato_brasileiro.csv: EC Vitória (Salvador, BA)
  # is listed with UF "ES" in several seasons.
  defp fix_uf("Vitória", "ES"), do: "BA"
  defp fix_uf(_name, uf), do: uf

  defp load_copa(path) do
    for row <- CSV.parse_file_to_maps(path),
        date = parse_date(row["datetime"]),
        date != nil do
      home = TeamNames.normalize(row["home_team"])
      away = TeamNames.normalize(row["away_team"])

      %Match{
        source: :copa,
        competition: :copa_do_brasil,
        date: date,
        time: parse_time(row["datetime"]),
        season: parse_int(row["season"]),
        round: row["round"],
        home: home.display,
        away: away.display,
        home_key: home.key,
        away_key: away.key,
        home_goal: parse_int(row["home_goal"]),
        away_goal: parse_int(row["away_goal"])
      }
    end
  end

  defp load_libertadores(path) do
    for row <- CSV.parse_file_to_maps(path),
        date = parse_date(row["datetime"]),
        date != nil do
      home = TeamNames.normalize(row["home_team"])
      away = TeamNames.normalize(row["away_team"])

      %Match{
        source: :libertadores,
        competition: :libertadores,
        date: date,
        time: parse_time(row["datetime"]),
        season: parse_int(row["season"]),
        stage: row["stage"],
        home: home.display,
        away: away.display,
        home_key: home.key,
        away_key: away.key,
        home_goal: parse_int(row["home_goal"]),
        away_goal: parse_int(row["away_goal"])
      }
    end
  end

  @extended_competitions %{
    "Serie A" => :brasileirao,
    "Serie B" => :serie_b,
    "Serie C" => :serie_c,
    "Copa do Brasil" => :copa_do_brasil,
    "Libertadores" => :libertadores
  }

  defp load_extended(path) do
    for row <- CSV.parse_file_to_maps(path),
        date = parse_date(row["date"]),
        date != nil do
      home = TeamNames.normalize(row["home"])
      away = TeamNames.normalize(row["away"])

      %Match{
        source: :extended,
        competition: Map.get(@extended_competitions, row["tournament"], :other),
        date: date,
        time: row["time"],
        season: date.year,
        home: home.display,
        away: away.display,
        home_key: home.key,
        away_key: away.key,
        home_goal: parse_int(row["home_goal"]),
        away_goal: parse_int(row["away_goal"]),
        extras:
          drop_blank(%{
            "home_corners" => row["home_corner"],
            "away_corners" => row["away_corner"],
            "home_shots" => row["home_shots"],
            "away_shots" => row["away_shots"],
            "home_attacks" => row["home_attack"],
            "away_attacks" => row["away_attack"],
            "ht_result" => row["ht_result"]
          })
      }
    end
  end

  @skill_columns ~w(Crossing Finishing HeadingAccuracy ShortPassing Volleys Dribbling
    Curve FKAccuracy LongPassing BallControl Acceleration SprintSpeed Agility
    Reactions Balance ShotPower Jumping Stamina Strength LongShots Aggression
    Interceptions Positioning Vision Penalties Composure Marking StandingTackle
    SlidingTackle GKDiving GKHandling GKKicking GKPositioning GKReflexes)

  defp load_players(path) do
    for row <- CSV.parse_file_to_maps(path), row["Name"] not in [nil, ""] do
      skills =
        for col <- @skill_columns, v = parse_int(row[col]), v != nil, into: %{} do
          {col, v}
        end

      %Player{
        id: parse_int(row["ID"]),
        name: row["Name"],
        name_search: TeamNames.clean(row["Name"]),
        age: parse_int(row["Age"]),
        nationality: row["Nationality"],
        overall: parse_int(row["Overall"]),
        potential: parse_int(row["Potential"]),
        club: blank_to_nil(row["Club"]),
        club_search: TeamNames.clean(row["Club"] || ""),
        position: blank_to_nil(row["Position"]),
        jersey_number: parse_int(row["Jersey Number"]),
        height: blank_to_nil(row["Height"]),
        weight: blank_to_nil(row["Weight"]),
        value: blank_to_nil(row["Value"]),
        wage: blank_to_nil(row["Wage"]),
        preferred_foot: blank_to_nil(row["Preferred Foot"]),
        skills: skills
      }
    end
  end

  # -- dedup and registry ----------------------------------------------------

  # Input is concatenated in source-priority order, so on a collision the
  # already-stored record is the higher-priority one and only gains extras.
  # Kick-off dates differ by a day between sources for the same fixture
  # (timezone handling), so a pair played within +/- 1 day is the same match.
  defp dedupe(matches) do
    matches
    |> Enum.reduce(%{}, fn m, acc ->
      case existing_key(acc, m) do
        nil ->
          Map.put(acc, {m.date, m.home_key, m.away_key}, m)

        key ->
          Map.update!(acc, key, &merge_duplicate(&1, m))
      end
    end)
    |> Map.values()
    |> Enum.sort_by(& &1.date, Date)
  end

  # The kept (higher-priority) record wins, but gains extras and any score it
  # is missing — e.g. postponed fixtures listed without a result in the
  # primary file whose played result appears in another source.
  defp merge_duplicate(kept, dup) do
    %{
      kept
      | extras: Map.merge(dup.extras, kept.extras),
        home_goal: kept.home_goal || dup.home_goal,
        away_goal: kept.away_goal || dup.away_goal
    }
  end

  defp existing_key(acc, m) do
    Enum.find_value([0, -1, 1], fn offset ->
      key = {Date.add(m.date, offset), m.home_key, m.away_key}
      if Map.has_key?(acc, key), do: key
    end)
  end

  defp build_registry(matches) do
    teams =
      Enum.reduce(matches, %{}, fn m, acc ->
        acc
        |> register(m.home_key, m.home)
        |> register(m.away_key, m.away)
      end)

    # A base name shared by several keys (América-MG vs América-RN) is
    # ambiguous: display it with its state suffix.
    ambiguous =
      teams
      |> Map.values()
      |> Enum.frequencies_by(& &1.base)
      |> Enum.filter(fn {_base, n} -> n > 1 end)
      |> MapSet.new(fn {base, _} -> base end)

    Map.new(teams, fn {key, t} ->
      # Famous clubs (the base name's default state) keep their plain name;
      # namesakes from other states get the suffix: "Flamengo" but "Flamengo-PI".
      suffix? =
        MapSet.member?(ambiguous, t.base) and t.state != nil and
          TeamNames.default_state(t.base) != t.state

      display = if suffix?, do: "#{t.raw_display}-#{t.state}", else: t.raw_display

      {key, %{key: key, base: t.base, state: t.state, display: display}}
    end)
  end

  defp register(acc, key, display) do
    norm = TeamNames.normalize(display)

    Map.update(
      acc,
      key,
      %{base: norm.base, state: state_from_key(key, norm), raw_display: display},
      fn t ->
        # Prefer the cleanest display spelling: no periods, then shortest.
        if better_display?(display, t.raw_display),
          do: %{t | raw_display: display},
          else: t
      end
    )
  end

  defp state_from_key(key, norm) do
    case String.split(key, "-") |> List.last() do
      code when byte_size(code) in [2, 3] -> TeamNames.normalize_state(code) || norm.state
      _ -> norm.state
    end
  end

  defp better_display?(a, b) do
    {String.contains?(a, "."), String.length(a)} < {String.contains?(b, "."), String.length(b)}
  end

  # -- parsing helpers -------------------------------------------------------

  @doc "Parse ISO (\"2023-09-24\"), ISO datetime, or Brazilian (\"29/03/2003\") dates."
  def parse_date(nil), do: nil
  def parse_date(""), do: nil

  def parse_date(s) do
    s = String.trim(s)

    cond do
      m = Regex.run(~r/^(\d{4})-(\d{2})-(\d{2})/, s) ->
        [_, y, mo, d] = m
        new_date(y, mo, d)

      m = Regex.run(~r/^(\d{1,2})\/(\d{1,2})\/(\d{4})/, s) ->
        [_, d, mo, y] = m
        new_date(y, mo, d)

      true ->
        nil
    end
  end

  defp new_date(y, m, d) do
    case Date.new(String.to_integer(y), String.to_integer(m), String.to_integer(d)) do
      {:ok, date} -> date
      _ -> nil
    end
  end

  defp parse_time(s) do
    case Regex.run(~r/(\d{2}:\d{2}(?::\d{2})?)/, to_string(s)) do
      [_, t] -> t
      _ -> nil
    end
  end

  @doc "Lenient integer parse: handles \"2\", \"2.0\", \"88+2\", returns nil otherwise."
  def parse_int(nil), do: nil
  def parse_int(i) when is_integer(i), do: i
  def parse_int(f) when is_float(f), do: trunc(f)

  def parse_int(s) when is_binary(s) do
    case Integer.parse(String.trim(s)) do
      {i, _rest} -> i
      :error -> nil
    end
  end

  defp blank_to_nil(nil), do: nil
  defp blank_to_nil(s), do: if(String.trim(s) == "", do: nil, else: s)

  defp drop_blank(map) do
    for {k, v} <- map, v not in [nil, ""], into: %{}, do: {k, v}
  end
end
