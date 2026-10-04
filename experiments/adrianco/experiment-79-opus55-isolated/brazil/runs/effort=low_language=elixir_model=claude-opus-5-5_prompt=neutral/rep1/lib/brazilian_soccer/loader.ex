defmodule BrazilianSoccer.Loader do
  @moduledoc """
  Loads the six Kaggle CSV files into unified in-memory structures.

  Several files cover the same fixtures (e.g. Serie A 2014-2019 appears in
  three of them). Matches with the same competition and teams played within
  two days of each other are merged into one record, so statistics are not
  double counted; the merged record keeps every source plus the extra fields
  (round, arena, corner/shot statistics) each file contributes.
  """

  alias BrazilianSoccer.{CSV, Match, Teams, Text}

  @serie_a "Brasileirão Série A"
  @serie_b "Brasileirão Série B"
  @serie_c "Brasileirão Série C"
  @cup "Copa do Brasil"
  @libertadores "Copa Libertadores"

  @files %{
    historical: "novo_campeonato_brasileiro.csv",
    brasileirao: "Brasileirao_Matches.csv",
    cup: "Brazilian_Cup_Matches.csv",
    libertadores: "Libertadores_Matches.csv",
    extended: "BR-Football-Dataset.csv",
    fifa: "fifa_data.csv"
  }

  def files, do: @files
  def competitions, do: [@serie_a, @serie_b, @serie_c, @cup, @libertadores]

  @doc "Loads everything from `dir`. Raises if a file is missing."
  def load(dir) do
    rows = fn id -> dir |> Path.join(@files[id]) |> File.read!() |> CSV.parse_maps() end

    per_file = [
      {:historical, rows.(:historical) |> Enum.map(&historical/1)},
      {:brasileirao, rows.(:brasileirao) |> Enum.map(&brasileirao/1)},
      {:cup, rows.(:cup) |> Enum.map(&cup/1) |> label_cup_stages()},
      {:libertadores, rows.(:libertadores) |> Enum.map(&libertadores/1)},
      {:extended, rows.(:extended) |> Enum.map(&extended/1)}
    ]

    per_file = Enum.map(per_file, fn {id, ms} -> {id, Enum.reject(ms, &is_nil(&1.date))} end)
    matches = per_file |> Enum.flat_map(&elem(&1, 1)) |> merge_duplicates()
    players = rows.(:fifa) |> Enum.map(&player/1) |> Enum.reject(&(&1.name == ""))

    team_counts =
      Enum.reduce(matches, %{}, fn m, acc ->
        acc |> Map.update(m.home_key, 1, &(&1 + 1)) |> Map.update(m.away_key, 1, &(&1 + 1))
      end)

    %{
      matches: matches,
      players: players,
      team_counts: team_counts,
      file_counts:
        Map.new(per_file, fn {id, ms} -> {@files[id], length(ms)} end)
        |> Map.put(@files[:fifa], length(players))
    }
  end

  # ── per-file row converters ────────────────────────────────────────────

  defp historical(r) do
    home = r["Equipe_mandante"] || ""
    away = r["Equipe_visitante"] || ""

    base(home, away, trusted_uf(home, r["Mandante_UF"]), trusted_uf(away, r["Visitante_UF"]))
    |> Map.merge(%{
      date: Text.parse_date(r["Data"]),
      season: Text.parse_int(r["Ano"]),
      competition: @serie_a,
      round: Text.parse_int(r["Rodada"]),
      home_goals: Text.parse_int(r["Gols_mandante"]),
      away_goals: Text.parse_int(r["Gols_visitante"]),
      arena: presence(r["Arena"]),
      sources: [@files.historical]
    })
  end

  # The UF columns of this file contain errors for well-known clubs (Bahia
  # as "BH", Vitória as "ES"), so they are only used for other teams.
  defp trusted_uf(name, uf) do
    if Teams.brazilian_club?(Teams.resolve(name).key), do: nil, else: uf
  end

  defp brasileirao(r) do
    base(r["home_team"], r["away_team"], r["home_team_state"], r["away_team_state"])
    |> Map.merge(%{
      date: Text.parse_date(r["datetime"]),
      time: time_of(r["datetime"]),
      season: Text.parse_int(r["season"]),
      competition: @serie_a,
      round: Text.parse_int(r["round"]),
      home_goals: Text.parse_int(r["home_goal"]),
      away_goals: Text.parse_int(r["away_goal"]),
      sources: [@files.brasileirao]
    })
  end

  defp cup(r) do
    base(r["home_team"], r["away_team"])
    |> Map.merge(%{
      date: Text.parse_date(r["datetime"]),
      time: time_of(r["datetime"]),
      season: Text.parse_int(r["season"]),
      competition: @cup,
      round: Text.parse_int(r["round"]),
      home_goals: Text.parse_int(r["home_goal"]),
      away_goals: Text.parse_int(r["away_goal"]),
      sources: [@files.cup]
    })
  end

  defp libertadores(r) do
    base(r["home_team"], r["away_team"])
    |> Map.merge(%{
      date: Text.parse_date(r["datetime"]),
      time: time_of(r["datetime"]),
      season: Text.parse_int(r["season"]),
      competition: @libertadores,
      stage: presence(r["stage"]),
      home_goals: Text.parse_int(r["home_goal"]),
      away_goals: Text.parse_int(r["away_goal"]),
      sources: [@files.libertadores]
    })
  end

  defp extended(r) do
    date = Text.parse_date(r["date"])

    competition =
      case r["tournament"] do
        "Serie A" -> @serie_a
        "Serie B" -> @serie_b
        "Serie C" -> @serie_c
        "Copa do Brasil" -> @cup
        other -> other
      end

    stats =
      for k <-
            ~w(home_corner away_corner home_attack away_attack home_shots away_shots total_corners),
          v = Text.parse_int(r[k]),
          into: %{},
          do: {k, v}

    base(r["home"], r["away"])
    |> Map.merge(%{
      date: date,
      time: presence(r["time"]),
      season: date && extended_season(date, competition),
      competition: competition,
      home_goals: Text.parse_int(r["home_goal"]),
      away_goals: Text.parse_int(r["away_goal"]),
      stats: if(stats == %{}, do: nil, else: stats),
      sources: [@files.extended]
    })
  end

  # This file has no season column. Seasons follow the calendar year, except
  # the pandemic-delayed 2020 season which finished in early 2021.
  defp extended_season(%Date{year: 2021} = d, @cup),
    do: if(Date.compare(d, ~D[2021-03-08]) == :lt, do: 2020, else: 2021)

  defp extended_season(%Date{year: 2021} = d, _),
    do: if(Date.compare(d, ~D[2021-04-01]) == :lt, do: 2020, else: 2021)

  defp extended_season(d, _), do: d.year

  defp base(home, away, home_uf \\ nil, away_uf \\ nil) do
    h = Teams.resolve(home || "", home_uf)
    a = Teams.resolve(away || "", away_uf)

    %Match{
      home: h.name,
      away: a.name,
      home_key: h.key,
      away_key: a.key,
      home_state: h.state,
      away_state: a.state
    }
  end

  defp time_of(nil), do: nil

  defp time_of(s) do
    case Regex.run(~r/(\d{2}:\d{2})(:\d{2})?$/, String.trim(s)) do
      [_, hm | _] -> hm <> ":00"
      _ -> nil
    end
  end

  defp presence(s), do: if(Text.blank?(s), do: nil, else: String.trim(s))

  # The cup file only numbers its rounds. When a season's last round has at
  # most two matches (the two legs of the final) the closing rounds are named.
  defp label_cup_stages(matches) do
    finals =
      matches
      |> Enum.filter(& &1.round)
      |> Enum.group_by(& &1.season)
      |> Enum.flat_map(fn {season, ms} ->
        max = ms |> Enum.map(& &1.round) |> Enum.max()
        if Enum.count(ms, &(&1.round == max)) <= 2, do: [{season, max}], else: []
      end)
      |> Map.new()

    Enum.map(matches, fn m ->
      stage =
        case finals[m.season] do
          nil -> nil
          max when m.round == max -> "final"
          max when m.round == max - 1 -> "semifinals"
          max when m.round == max - 2 -> "quarterfinals"
          max when m.round == max - 3 -> "round of 16"
          _ -> nil
        end

      %{m | stage: stage}
    end)
  end

  # ── de-duplication ─────────────────────────────────────────────────────

  defp merge_duplicates(matches) do
    {_index, kept} =
      Enum.reduce(matches, {%{}, %{}}, fn m, {index, kept} ->
        k = {m.competition, m.home_key, m.away_key}
        candidates = Map.get(index, k, [])

        dup =
          Enum.find(candidates, fn id ->
            other = kept[id]
            abs(Date.diff(other.date, m.date)) <= 2 and compatible_state?(other, m)
          end)

        if dup do
          {index, Map.update!(kept, dup, &merge(&1, m))}
        else
          id = map_size(kept)
          {Map.put(index, k, [id | candidates]), Map.put(kept, id, m)}
        end
      end)

    kept
    |> Map.values()
    |> Enum.sort_by(&{Date.to_erl(&1.date), &1.competition, &1.home}, :desc)
  end

  defp compatible_state?(a, b) do
    ok = fn x, y -> x == nil or y == nil or x == y end
    ok.(a.home_state, b.home_state) and ok.(a.away_state, b.away_state)
  end

  defp merge(%Match{} = a, %Match{} = b) do
    %{
      a
      | time: a.time || b.time,
        round: a.round || b.round,
        stage: a.stage || b.stage,
        arena: a.arena || b.arena,
        stats: a.stats || b.stats,
        home_goals: a.home_goals || b.home_goals,
        away_goals: a.away_goals || b.away_goals,
        home_state: a.home_state || b.home_state,
        away_state: a.away_state || b.away_state,
        sources: Enum.uniq(a.sources ++ b.sources)
    }
  end

  # ── players ────────────────────────────────────────────────────────────

  @skills ~w(Crossing Finishing HeadingAccuracy ShortPassing Volleys Dribbling Curve
             FKAccuracy LongPassing BallControl Acceleration SprintSpeed Agility Reactions
             Balance ShotPower Jumping Stamina Strength LongShots Aggression Interceptions
             Positioning Vision Penalties Composure Marking StandingTackle SlidingTackle
             GKDiving GKHandling GKKicking GKPositioning GKReflexes)

  defp player(r) do
    club = presence(r["Club"])

    %{
      id: Text.parse_int(r["ID"]),
      name: String.trim(r["Name"] || ""),
      age: Text.parse_int(r["Age"]),
      nationality: presence(r["Nationality"]),
      overall: Text.parse_int(r["Overall"]),
      potential: Text.parse_int(r["Potential"]),
      club: club,
      position: presence(r["Position"]),
      jersey_number: Text.parse_int(r["Jersey Number"]),
      height: presence(r["Height"]),
      weight: presence(r["Weight"]),
      preferred_foot: presence(r["Preferred Foot"]),
      value: presence(r["Value"]),
      wage: presence(r["Wage"]),
      skills: for(k <- @skills, v = Text.parse_int(r[k]), into: %{}, do: {k, v}),
      name_fold: Text.fold(r["Name"]),
      nationality_fold: Text.fold(r["Nationality"]),
      club_fold: Text.fold(club),
      club_key: club && Teams.resolve(club).key
    }
  end
end
