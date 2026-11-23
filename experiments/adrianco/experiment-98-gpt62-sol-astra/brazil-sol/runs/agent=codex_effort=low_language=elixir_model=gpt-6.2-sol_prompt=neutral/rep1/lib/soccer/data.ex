defmodule Soccer.Data do
  @moduledoc "Loads the local match and FIFA datasets and links their club identities."
  alias Soccer.{CSV, Names}

  @historical "novo_campeonato_brasileiro.csv"
  @league "Brasileirao_Matches.csv"
  @cup "Brazilian_Cup_Matches.csv"
  @libertadores "Libertadores_Matches.csv"
  @extended "BR-Football-Dataset.csv"
  @fifa "fifa_data.csv"
  @serie_a "Brasileirão Série A"
  @copa "Copa do Brasil"

  def load!(directory) do
    raw =
      Map.new([@historical, @league, @cup, @libertadores, @extended], fn file ->
        rows = CSV.read!(Path.join(directory, file))
        {file, rows |> Enum.map(&match(&1, file)) |> mark_cup_finals(file)}
      end)

    {historical_league, later_league} =
      Enum.split_with(raw[@league], &(&1.season <= 2019))

    league_index = Enum.group_by(historical_league, &league_key/1)

    historical =
      Enum.map(raw[@historical], fn match ->
        case Map.get(league_index, league_key(match), []) do
          [candidate] ->
            merge(match, candidate)

          candidates ->
            case match.date && nearest(candidates, match.date) do
              nil -> match
              candidate -> merge(match, candidate)
            end
        end
      end)

    primary = historical ++ later_league ++ raw[@cup] ++ raw[@libertadores]

    index = Enum.group_by(primary, &fixture_key/1)

    league_seasons =
      primary |> Enum.filter(&(&1.competition == @serie_a)) |> MapSet.new(& &1.season)

    {updates, additional} =
      Enum.reduce(raw[@extended], {%{}, []}, fn match, {updates, additional} ->
        candidates = Map.get(index, fixture_key(match), [])
        nearby = match.date && nearest(candidates, match.date)

        covered_league =
          match.competition == @serie_a and MapSet.member?(league_seasons, match.season)

        rescheduled =
          if covered_league and !nearby do
            case Enum.filter(candidates, &(&1.season == match.season)) do
              [%{home_goal: nil, away_goal: nil} = fixture] -> fixture
              _ -> nil
            end
          end

        cond do
          fixture = nearby || rescheduled ->
            updated = Map.get(updates, id(fixture), fixture)

            updated =
              if rescheduled, do: %{updated | date: match.date, time: match.time}, else: updated

            {Map.put(updates, id(fixture), merge(updated, match)), additional}

          covered_league ->
            {updates, additional}

          true ->
            {updates, [match | additional]}
        end
      end)

    matches =
      primary
      |> Enum.map(&Map.get(updates, id(&1), &1))
      |> Kernel.++(
        Enum.uniq_by(additional, &{fixture_key(&1), &1.date, &1.home_goal, &1.away_goal})
      )
      |> sort_matches()

    players = CSV.read!(Path.join(directory, @fifa)) |> Enum.map(&player/1)
    counts = Map.new(raw, fn {file, matches} -> {file, length(matches)} end)

    %{
      matches: matches,
      sources: Map.new(raw, fn {k, v} -> {k, sort_matches(v)} end),
      players: players,
      counts: Map.put(counts, @fifa, length(players)),
      clubs:
        matches
        |> Enum.reject(&(&1.competition == "Copa Libertadores"))
        |> Enum.flat_map(&[&1.home_key, &1.away_key])
        |> MapSet.new()
    }
  end

  def sort_matches(matches) do
    Enum.sort_by(matches, &{&1.date || "", &1.time || "", &1.home_team, &1.away_team}, :desc)
  end

  def date(value) do
    date = value |> String.trim() |> String.split(~r/[ T]/, parts: 2) |> hd()

    iso =
      case String.split(date, "/") do
        [day, month, year] ->
          Enum.join(
            [year, String.pad_leading(month, 2, "0"), String.pad_leading(day, 2, "0")],
            "-"
          )

        [_] ->
          date

        _ ->
          ""
      end

    case Date.from_iso8601(iso) do
      {:ok, parsed} -> Date.to_iso8601(parsed)
      _ -> nil
    end
  end

  defp number(value) do
    case Float.parse(value || "") do
      {n, ""} when trunc(n) == n -> trunc(n)
      {n, ""} -> n
      _ -> nil
    end
  end

  defp match(row, @historical) do
    build(
      @historical,
      @serie_a,
      row["Equipe_mandante"],
      row["Equipe_visitante"],
      row["Data"],
      row["Ano"],
      row["Gols_mandante"],
      row["Gols_visitante"],
      %{
        round: number(row["Rodada"]),
        stadium: row["Arena"],
        source_id: row["ID"],
        home_state: row["Mandante_UF"],
        away_state: row["Visitante_UF"]
      }
    )
  end

  defp match(row, @extended) do
    competition = Names.competition(row["tournament"])
    date = date(row["date"])
    season = extended_season(competition, date)

    metrics =
      ~w(home_corner away_corner home_attack away_attack home_shots away_shots total_corners ht_diff at_diff)

    stats =
      Map.new(metrics, &{&1, number(row[&1])})
      |> Map.merge(Map.take(row, ~w(ht_result at_result)))

    build(
      @extended,
      competition,
      row["home"],
      row["away"],
      row["date"],
      season,
      row["home_goal"],
      row["away_goal"],
      %{time: row["time"], statistics: stats}
    )
  end

  defp match(row, file) do
    competition =
      %{@league => @serie_a, @cup => @copa, @libertadores => "Copa Libertadores"}[file]

    time = row["datetime"] |> String.split(" ", parts: 2) |> Enum.at(1)

    build(
      file,
      competition,
      row["home_team"],
      row["away_team"],
      row["datetime"],
      row["season"],
      row["home_goal"],
      row["away_goal"],
      %{
        time: time,
        round: number(row["round"]),
        stage: row["stage"],
        home_state: row["home_team_state"],
        away_state: row["away_team_state"]
      }
    )
  end

  defp build(source, competition, home, away, datetime, season, home_goal, away_goal, fields) do
    {home_key, home_team} = Names.club(home)
    {away_key, away_team} = Names.club(away)

    %{
      date: date(datetime),
      time: nil,
      season: number(season),
      competition: competition,
      home_team: home_team,
      home_key: home_key,
      away_team: away_team,
      away_key: away_key,
      home_goal: number(home_goal),
      away_goal: number(away_goal),
      round: nil,
      stage: nil,
      sources: [source]
    }
    |> Map.merge(fields)
  end

  # The pandemic shifted the end of the 2020 editions into 2021.
  defp extended_season(@copa, "2021-" <> _ = date) when date <= "2021-03-08", do: "2020"

  defp extended_season("Brasileirão Série A", "2021-" <> _ = date) when date <= "2021-02-28",
    do: "2020"

  defp extended_season("Brasileirão Série B", "2021-" <> _ = date) when date <= "2021-01-31",
    do: "2020"

  defp extended_season("Brasileirão Série C", "2021-" <> _ = date) when date <= "2021-02-01",
    do: "2020"

  defp extended_season(_, date), do: date && String.slice(date, 0, 4)

  defp mark_cup_finals(matches, @cup) do
    # The 2021 primary cup file ends at the round of 16.
    finals = %{2012 => 6, 2016 => 7, 2021 => nil}

    Enum.map(matches, fn match ->
      if match.round == Map.get(finals, match.season, 8),
        do: %{match | stage: "final"},
        else: match
    end)
  end

  defp mark_cup_finals(matches, @extended) do
    finals =
      matches
      |> Enum.filter(&(&1.competition == @copa and &1.season in 2021..2023))
      |> Enum.group_by(& &1.season)
      |> Enum.flat_map(fn {_, fixtures} ->
        case Enum.take(sort_matches(fixtures), 2) do
          [a, b] when a.home_key == b.away_key and a.away_key == b.home_key -> [id(a), id(b)]
          _ -> []
        end
      end)
      |> MapSet.new()

    Enum.map(matches, fn match ->
      if MapSet.member?(finals, id(match)), do: %{match | stage: "final"}, else: match
    end)
  end

  defp mark_cup_finals(matches, _), do: matches

  defp fixture_key(match), do: {match.competition, match.home_key, match.away_key}
  defp league_key(match), do: {fixture_key(match), match.season}
  defp id(match), do: {league_key(match), match.date, match.round, match.sources}

  defp nearest(matches, date) do
    parsed = Date.from_iso8601!(date)

    matches
    |> Enum.filter(& &1.date)
    |> Enum.map(&{abs(Date.diff(Date.from_iso8601!(&1.date), parsed)), &1})
    |> Enum.filter(fn {distance, _} -> distance <= 2 end)
    |> Enum.min_by(&elem(&1, 0), fn -> {nil, nil} end)
    |> elem(1)
  end

  defp merge(preferred, supplemental) do
    fields = [
      :date,
      :time,
      :round,
      :stage,
      :stadium,
      :source_id,
      :home_state,
      :away_state,
      :statistics,
      :home_goal,
      :away_goal
    ]

    preferred
    |> Map.merge(Map.take(supplemental, fields), fn _, primary, secondary ->
      primary || secondary
    end)
    |> Map.put(:sources, Enum.uniq(preferred.sources ++ supplemental.sources))
  end

  defp player(row) do
    {club_key, club_name} = Names.club(row["Club"])
    core = ~w(ID Name Age Nationality Overall Potential Club Position)
    attributes = Map.drop(row, ["" | core])

    %{
      id: number(row["ID"]),
      name: row["Name"],
      name_key: Names.fold(row["Name"]),
      nationality: row["Nationality"],
      nationality_key: Names.fold(row["Nationality"]),
      club: row["Club"],
      club_key: club_key,
      club_name: club_name,
      age: number(row["Age"]),
      overall: number(row["Overall"]),
      potential: number(row["Potential"]),
      position: row["Position"],
      attributes: attributes
    }
  end
end
