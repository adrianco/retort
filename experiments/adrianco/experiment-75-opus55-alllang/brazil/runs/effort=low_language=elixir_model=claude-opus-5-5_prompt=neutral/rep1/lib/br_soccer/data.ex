defmodule BrSoccer.Data do
  @moduledoc """
  Loads all six Kaggle CSV files into normalized in-memory records
  (kept in :persistent_term for fast, lock-free reads).
  """

  alias BrSoccer.{CSV, Team}

  @competitions %{
    serie_a: "Brasileirão Série A",
    serie_b: "Brasileirão Série B",
    serie_c: "Brasileirão Série C",
    copa_do_brasil: "Copa do Brasil",
    libertadores: "Copa Libertadores"
  }

  @skills ~w(Crossing Finishing Dribbling ShortPassing BallControl Acceleration SprintSpeed Reactions Stamina Strength Vision Composure StandingTackle GKDiving GKReflexes)

  def data_dir do
    Application.get_env(:br_soccer, :data_dir) ||
      Path.expand("../../data/kaggle", __DIR__)
  end

  def competition_name(c), do: Map.fetch!(@competitions, c)
  def competitions, do: Map.keys(@competitions)

  @doc "Parses a free-text competition name into an atom (nil = all)."
  def parse_competition(nil), do: nil
  def parse_competition(""), do: nil

  def parse_competition(str) do
    s = str |> Team.ascii() |> String.downcase()

    cond do
      s in ["all", "any"] -> nil
      s =~ "libertadores" -> :libertadores
      s =~ "copa do brasil" or s =~ "cup" or s == "copa_do_brasil" -> :copa_do_brasil
      s =~ ~r/serie[ _]?b/ -> :serie_b
      s =~ ~r/serie[ _]?c/ -> :serie_c
      s =~ "brasileir" or s =~ ~r/serie[ _]?a/ -> :serie_a
      true -> :unknown
    end
  end

  def load do
    unless loaded?() do
      matches = load_matches()
      players = load_players()
      :persistent_term.put({__MODULE__, :matches}, matches)
      :persistent_term.put({__MODULE__, :players}, players)
    end

    :ok
  end

  def loaded?, do: :persistent_term.get({__MODULE__, :matches}, nil) != nil

  def matches, do: :persistent_term.get({__MODULE__, :matches})
  def players, do: :persistent_term.get({__MODULE__, :players})

  # ---------------------------------------------------------------- matches

  defp load_matches do
    dir = data_dir()

    sources = [
      {"Brasileirao_Matches.csv", &brasileirao/1},
      {"novo_campeonato_brasileiro.csv", &novo/1},
      {"Brazilian_Cup_Matches.csv", &cup/1},
      {"Libertadores_Matches.csv", &libertadores/1},
      {"BR-Football-Dataset.csv", &br_football/1}
    ]

    {list, _seen} =
      sources
      |> Enum.flat_map(fn {file, fun} ->
        dir |> Path.join(file) |> CSV.read_maps() |> Enum.map(&Map.put(fun.(&1), :source, file))
      end)
      |> Enum.reject(&is_nil(&1.date))
      |> Enum.reduce({[], MapSet.new()}, fn m, {acc, seen} ->
        key = dedup_key(m)

        if MapSet.member?(seen, key),
          do: {acc, seen},
          else: {[m | acc], MapSet.put(seen, key)}
      end)

    Enum.sort_by(list, & &1.date, {:desc, Date})
  end

  # A league pairing is played once per season at each venue; cups are keyed by date.
  defp dedup_key(%{competition: c} = m) when c in [:serie_a, :serie_b, :serie_c],
    do: {c, m.season, m.home_key, m.away_key}

  # A team plays at most one cup match per day, so date + home team is enough.
  defp dedup_key(m), do: {m.competition, m.date, m.home_key}

  defp match(home, away, hg, ag, date, season, comp, extra) do
    date = parse_date(date)

    Map.merge(
      %{
        date: date,
        season: parse_int(season) || (date && date.year),
        home: clean_name(home),
        away: clean_name(away),
        home_key: Team.canonical(home),
        away_key: Team.canonical(away),
        home_goal: parse_int(hg),
        away_goal: parse_int(ag),
        competition: comp,
        round: nil,
        stage: nil
      },
      extra
    )
  end

  defp brasileirao(r) do
    match(r["home_team"], r["away_team"], r["home_goal"], r["away_goal"], r["datetime"], r["season"], :serie_a,
      %{round: parse_int(r["round"])})
  end

  defp novo(r) do
    match(r["Equipe_mandante"], r["Equipe_visitante"], r["Gols_mandante"], r["Gols_visitante"], r["Data"], r["Ano"],
      :serie_a, %{round: parse_int(r["Rodada"]), arena: blank_nil(r["Arena"])})
  end

  defp cup(r) do
    match(r["home_team"], r["away_team"], r["home_goal"], r["away_goal"], r["datetime"], r["season"], :copa_do_brasil,
      %{round: parse_int(r["round"])})
  end

  defp libertadores(r) do
    match(r["home_team"], r["away_team"], r["home_goal"], r["away_goal"], r["datetime"], r["season"], :libertadores,
      %{stage: blank_nil(r["stage"])})
  end

  defp br_football(r) do
    comp =
      case r["tournament"] do
        "Serie A" -> :serie_a
        "Serie B" -> :serie_b
        "Serie C" -> :serie_c
        _ -> :copa_do_brasil
      end

    date = parse_date(r["date"])
    # The 2020 Brazilian league season was played until February 2021.
    season =
      cond do
        is_nil(date) -> nil
        comp != :copa_do_brasil and date.year == 2021 and date.month <= 2 -> 2020
        true -> date.year
      end

    stats =
      for k <- ~w(home_corner away_corner home_attack away_attack home_shots away_shots), into: %{} do
        {String.to_atom(k), parse_int(r[k])}
      end

    match(r["home"], r["away"], r["home_goal"], r["away_goal"], r["date"], season, comp, %{stats: stats})
  end

  defp clean_name(name), do: name |> String.trim()

  @doc "Parses ISO (2023-09-24), ISO with time, and Brazilian (29/03/2003) dates."
  def parse_date(nil), do: nil

  def parse_date(str) do
    str = String.trim(str)

    case Regex.run(~r/^(\d{4})-(\d{2})-(\d{2})/, str) do
      [_, y, m, d] ->
        to_date(y, m, d)

      nil ->
        case Regex.run(~r/^(\d{1,2})\/(\d{1,2})\/(\d{4})/, str) do
          [_, d, m, y] -> to_date(y, m, d)
          nil -> nil
        end
    end
  end

  defp to_date(y, m, d) do
    case Date.new(String.to_integer(y), String.to_integer(m), String.to_integer(d)) do
      {:ok, date} -> date
      _ -> nil
    end
  end

  def parse_int(nil), do: nil
  def parse_int(n) when is_integer(n), do: n

  def parse_int(str) do
    case Float.parse(String.trim(str)) do
      {f, _} -> trunc(f)
      :error -> nil
    end
  end

  defp blank_nil(nil), do: nil

  defp blank_nil(s) do
    case String.trim(s) do
      "" -> nil
      t -> t
    end
  end

  # ---------------------------------------------------------------- players

  defp load_players do
    data_dir()
    |> Path.join("fifa_data.csv")
    |> CSV.read_maps()
    |> Enum.map(fn r ->
      %{
        id: parse_int(r["ID"]),
        name: r["Name"],
        name_key: r["Name"] |> Team.ascii() |> String.downcase(),
        age: parse_int(r["Age"]),
        nationality: r["Nationality"],
        overall: parse_int(r["Overall"]),
        potential: parse_int(r["Potential"]),
        club: blank_nil(r["Club"]),
        club_key: Team.canonical(r["Club"] || ""),
        position: blank_nil(r["Position"]),
        jersey: parse_int(r["Jersey Number"]),
        height: blank_nil(r["Height"]),
        weight: blank_nil(r["Weight"]),
        value: blank_nil(r["Value"]),
        wage: blank_nil(r["Wage"]),
        foot: blank_nil(r["Preferred Foot"]),
        skills: Map.new(@skills, &{&1, parse_int(r[&1])})
      }
    end)
  end
end
