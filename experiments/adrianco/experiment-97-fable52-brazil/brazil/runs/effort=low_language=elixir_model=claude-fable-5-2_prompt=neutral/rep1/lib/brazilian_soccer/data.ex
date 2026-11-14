defmodule BrazilianSoccer.Data do
  @moduledoc """
  Loads the six Kaggle CSV files into one in-memory knowledge base:

    * matches from all five match files, with team names normalised to a
      canonical key and the same fixture reported by several files merged
      into one record (so statistics are not double counted);
    * a team registry (canonical key => display name, state, match count);
    * FIFA players, linked to the team registry through their club.

  The loaded data is cached in `:persistent_term`; `get/0` loads on first use.
  """

  alias BrazilianSoccer.{CSV, Match, Player, TeamNames, Text}

  defstruct matches: [], players: [], teams: %{}, files: %{}, dir: nil

  @serie_a "Brasileirão Série A"
  @serie_b "Brasileirão Série B"
  @serie_c "Brasileirão Série C"
  @cup "Copa do Brasil"
  @libertadores "Copa Libertadores"

  @files %{
    brasileirao: "Brasileirao_Matches.csv",
    cup: "Brazilian_Cup_Matches.csv",
    libertadores: "Libertadores_Matches.csv",
    br_football: "BR-Football-Dataset.csv",
    historical: "novo_campeonato_brasileiro.csv",
    fifa: "fifa_data.csv"
  }

  # Unsuffixed names of ambiguous clubs default to these states.
  @default_states %{"atletico" => "MG", "america" => "MG", "botafogo" => "RJ"}
  @display %{
    "atletico" => "Atlético-MG",
    "atletico-pr" => "Athletico-PR",
    "atletico-go" => "Atlético-GO",
    "america" => "América-MG",
    "botafogo" => "Botafogo-RJ",
    "csa" => "CSA",
    "crb" => "CRB",
    "abc" => "ABC",
    "asa" => "ASA",
    "ldu" => "LDU"
  }

  @attribute_columns ~w(Crossing Finishing HeadingAccuracy ShortPassing Volleys Dribbling Curve
    FKAccuracy LongPassing BallControl Acceleration SprintSpeed Agility Reactions Balance ShotPower
    Jumping Stamina Strength LongShots Aggression Interceptions Positioning Vision Penalties
    Composure Marking StandingTackle SlidingTackle GKDiving GKHandling GKKicking GKPositioning
    GKReflexes)

  def league?(comp), do: comp in [@serie_a, @serie_b, @serie_c]
  def competitions, do: [@serie_a, @serie_b, @serie_c, @cup, @libertadores]
  def files, do: @files

  @doc "Directory holding the CSV files (override with BRAZILIAN_SOCCER_DATA_DIR)."
  def default_dir do
    candidates =
      [
        System.get_env("BRAZILIAN_SOCCER_DATA_DIR"),
        Path.join(File.cwd!(), "data/kaggle"),
        unquote(Path.expand("../../data/kaggle", __DIR__))
      ]
      |> Enum.reject(&is_nil/1)

    Enum.find(candidates, List.first(candidates), &File.dir?/1)
  end

  @doc "Returns the cached dataset, loading it on first use."
  def get do
    case :persistent_term.get(__MODULE__, nil) do
      nil ->
        :global.trans({__MODULE__, self()}, fn ->
          case :persistent_term.get(__MODULE__, nil) do
            nil ->
              data = load!()
              :persistent_term.put(__MODULE__, data)
              data

            data ->
              data
          end
        end)

      data ->
        data
    end
  end

  @doc "Loads every CSV file from `dir` and builds the dataset."
  def load!(dir \\ default_dir()) do
    raw =
      [:brasileirao, :historical, :cup, :libertadores, :br_football]
      |> Task.async_stream(fn src -> {src, load_matches(src, dir)} end,
        timeout: :infinity,
        ordered: true
      )
      |> Enum.map(fn {:ok, v} -> v end)

    fifa_rows = CSV.read_maps!(Path.join(dir, @files.fifa))

    all = Enum.flat_map(raw, fn {_, {rows, _total}} -> rows end)
    registry = build_registry(all)

    {matches, merged} = all |> Enum.map(&to_match(&1, registry)) |> merge_duplicates()
    matches = drop_stray_league_rows(matches)

    matches =
      matches
      |> label_cup_finals()
      |> Enum.sort_by(&{Date.to_gregorian_days(&1.date), &1.id}, :desc)

    counts = Enum.frequencies(Enum.flat_map(matches, &[&1.home, &1.away]))

    teams =
      Map.new(registry.teams, fn {k, t} -> {k, Map.put(t, :matches, Map.get(counts, k, 0))} end)

    players = Enum.map(fifa_rows, &to_player(&1, teams, registry))

    files =
      raw
      |> Map.new(fn {src, {rows, total}} ->
        {src, %{file: @files[src], rows: total, played: length(rows)}}
      end)
      |> Map.put(:fifa, %{file: @files.fifa, rows: length(fifa_rows), played: nil})
      |> Map.put(:merged_duplicates, merged)

    %__MODULE__{matches: matches, players: players, teams: teams, files: files, dir: dir}
  end

  # ---------------------------------------------------------------- loading

  # Each loader returns {played_match_rows, total_row_count}. Rows without a
  # date or a score (fixtures not yet played) are skipped.
  defp load_matches(src, dir) do
    rows = CSV.read_maps!(Path.join(dir, @files[src]))
    parsed = rows |> Enum.map(&row(src, &1)) |> Enum.reject(&is_nil/1)
    {parsed, length(rows)}
  end

  defp row(:brasileirao, r) do
    base(
      :brasileirao,
      @serie_a,
      r["datetime"],
      r["home_team"],
      r["away_team"],
      r["home_goal"],
      r["away_goal"],
      %{
        season: Text.to_int(r["season"]),
        round: Text.to_int(r["round"])
      }
    )
  end

  # The state columns of this file are unreliable (Bahia is "BH", Vitória is
  # "ES"), so states are only taken from the team names themselves.
  defp row(:historical, r) do
    base(
      :historical,
      @serie_a,
      r["Data"],
      r["Equipe_mandante"],
      r["Equipe_visitante"],
      r["Gols_mandante"],
      r["Gols_visitante"],
      %{
        season: Text.to_int(r["Ano"]),
        round: Text.to_int(r["Rodada"]),
        arena: blank(r["Arena"])
      }
    )
  end

  defp row(:cup, r) do
    base(
      :cup,
      @cup,
      r["datetime"],
      r["home_team"],
      r["away_team"],
      r["home_goal"],
      r["away_goal"],
      %{
        season: Text.to_int(r["season"]),
        round: Text.to_int(r["round"]) || blank(r["round"])
      }
    )
  end

  defp row(:libertadores, r) do
    base(
      :libertadores,
      @libertadores,
      r["datetime"],
      r["home_team"],
      r["away_team"],
      r["home_goal"],
      r["away_goal"],
      %{
        season: Text.to_int(r["season"]),
        stage: blank(r["stage"])
      }
    )
  end

  defp row(:br_football, r) do
    comp =
      case Text.normalize(r["tournament"]) do
        "serie a" -> @serie_a
        "serie b" -> @serie_b
        "serie c" -> @serie_c
        "copa do brasil" -> @cup
        other -> other
      end

    stats =
      for {col, key} <- [
            {"home_corner", :home_corners},
            {"away_corner", :away_corners},
            {"home_attack", :home_attacks},
            {"away_attack", :away_attacks},
            {"home_shots", :home_shots},
            {"away_shots", :away_shots}
          ],
          v = Text.to_int(r[col]),
          into: %{},
          do: {key, v}

    date = if r["date"] in [nil, ""], do: nil, else: r["date"] <> " " <> (r["time"] || "")

    base(:br_football, comp, date, r["home"], r["away"], r["home_goal"], r["away_goal"], %{
      stats: stats
    })
  end

  defp base(src, comp, datetime, home, away, hg, ag, extra) do
    with {date, time} <- Text.parse_datetime(datetime),
         hg when is_integer(hg) <- Text.to_int(hg),
         ag when is_integer(ag) <- Text.to_int(ag),
         true <- is_binary(home) and is_binary(away) and home != "" and away != "" do
      {hb, hs, hl} = TeamNames.parse(home)
      {ab, as, al} = TeamNames.parse(away)

      # a few source rows list the same club on both sides; they are unusable
      if {hb, hs} == {ab, as}, do: throw(:invalid_row)

      Map.merge(
        %{
          source: src,
          competition: comp,
          date: date,
          time: time,
          season: extra[:season] || season_of(date, comp),
          home: {hb, hs, hl},
          away: {ab, as, al},
          home_goals: hg,
          away_goals: ag
        },
        Map.delete(extra, :season)
      )
    else
      _ -> nil
    end
  catch
    :invalid_row -> nil
  end

  # The 2020 domestic season was delayed by COVID-19 and finished in early 2021.
  defp season_of(date, comp) when comp != @libertadores do
    if Date.compare(date, ~D[2021-01-01]) != :lt and Date.compare(date, ~D[2021-03-08]) != :gt,
      do: 2020,
      else: date.year
  end

  defp season_of(date, _), do: date.year

  defp blank(nil), do: nil
  defp blank(s), do: if(String.trim(s) in ["", "NA"], do: nil, else: String.trim(s))

  # --------------------------------------------------------------- registry

  defp build_registry(rows) do
    sides = Enum.flat_map(rows, &[&1.home, &1.away])

    state_counts =
      Enum.reduce(sides, %{}, fn {b, s, _}, acc ->
        if s,
          do: Map.update(acc, b, %{s => 1}, &Map.update(&1, s, 1, fn n -> n + 1 end)),
          else: acc
      end)

    defaults =
      Map.new(state_counts, fn {b, states} ->
        {b,
         Map.get(@default_states, b) || states |> Enum.max_by(fn {s, n} -> {n, s} end) |> elem(0)}
      end)

    registry = %{defaults: defaults}

    labels =
      Enum.reduce(sides, %{}, fn {b, s, label}, acc ->
        k = key(registry, b, s)
        Map.update(acc, k, %{label => 1}, &Map.update(&1, label, 1, fn n -> n + 1 end))
      end)

    teams =
      sides
      |> Enum.map(fn {b, s, _} -> {b, s} end)
      |> Enum.uniq()
      |> Enum.reduce(%{}, fn {b, s}, acc ->
        k = key(registry, b, s)
        state = s || Map.get(defaults, b)
        existing = Map.get(acc, k)

        if existing && existing.state do
          acc
        else
          Map.put(acc, k, %{
            key: k,
            base: b,
            state: state,
            name: display(k, b, s, defaults, labels[k])
          })
        end
      end)

    Map.put(registry, :teams, teams)
  end

  @doc false
  def key(registry, base, state) do
    default = Map.get(registry.defaults, base)

    if state == nil or default == nil or state == default,
      do: base,
      else: base <> "-" <> String.downcase(state)
  end

  defp display(k, base, state, defaults, labels) do
    case Map.get(@display, k) do
      nil ->
        exact = Enum.filter(labels, fn {l, _} -> Text.normalize(l) == base end)

        name =
          case exact do
            [] ->
              base |> String.split(" ") |> Enum.map_join(" ", &String.capitalize/1)

            list ->
              list
              |> Enum.max_by(fn {l, n} ->
                {l != Text.normalize(l) and String.upcase(l) != l, non_ascii?(l), n}
              end)
              |> elem(0)
              |> titleize()
          end

        if state != nil and Map.get(defaults, base) != state, do: "#{name}-#{state}", else: name

      name ->
        name
    end
  end

  defp non_ascii?(s), do: String.match?(s, ~r/[^\x00-\x7F]/)
  defp titleize(s), do: if(s == String.downcase(s), do: String.capitalize(s), else: s)

  defp to_match(r, registry) do
    {hb, hs, _} = r.home
    {ab, as, _} = r.away
    hk = key(registry, hb, hs)
    ak = key(registry, ab, as)

    %Match{
      date: r.date,
      time: r.time,
      season: r.season,
      competition: r.competition,
      round: r[:round],
      stage: r[:stage],
      home: hk,
      away: ak,
      home_name: registry.teams[hk].name,
      away_name: registry.teams[ak].name,
      home_goals: r.home_goals,
      away_goals: r.away_goals,
      arena: r[:arena],
      stats: r[:stats] || %{},
      sources: [r.source]
    }
  end

  # ------------------------------------------------------------ duplicates

  # The same fixture can appear in up to three files. Two rows are the same
  # match when competition, home and away team agree and the dates are at most
  # one day apart (some files use UTC kick-off times) or, for leagues where a
  # fixture is played once per season, the season agrees. Rows are merged so each
  # file contributes what it knows (round, stadium, corners, shots ...).
  defp merge_duplicates(matches) do
    {by_id, _index, merged, _next} =
      Enum.reduce(matches, {%{}, %{}, 0, 1}, fn m, {by_id, index, merged, next} ->
        fixture = {m.competition, m.home, m.away}
        days = Date.to_gregorian_days(m.date)

        dup =
          index
          |> Map.get(fixture, [])
          |> Enum.find(fn {d, id} ->
            other = by_id[id]

            hd(m.sources) not in other.sources and
              (abs(d - days) <= 1 or (league?(m.competition) and other.season == m.season))
          end)

        case dup do
          {_, id} ->
            {Map.update!(by_id, id, &merge(&1, m)), index, merged + 1, next}

          nil ->
            m = %{m | id: next}

            {Map.put(by_id, next, m),
             Map.update(index, fixture, [{days, next}], &[{days, next} | &1]), merged, next + 1}
        end
      end)

    {Map.values(by_id), merged}
  end

  # BR-Football has a handful of league rows that contradict the official
  # files (reversed or mislabelled fixtures). When the other files already
  # hold the complete double round robin of a season, such rows are dropped.
  defp drop_stray_league_rows(matches) do
    complete =
      matches
      |> Enum.filter(&(league?(&1.competition) and &1.sources != [:br_football]))
      |> Enum.group_by(&{&1.competition, &1.season})
      |> Enum.filter(fn {_, ms} ->
        n = ms |> Enum.flat_map(&[&1.home, &1.away]) |> Enum.uniq() |> length()
        length(ms) == n * (n - 1)
      end)
      |> MapSet.new(&elem(&1, 0))

    Enum.reject(
      matches,
      &(&1.sources == [:br_football] and MapSet.member?(complete, {&1.competition, &1.season}))
    )
  end

  defp merge(a, b) do
    %{
      a
      | sources: a.sources ++ b.sources,
        time: a.time || b.time,
        round: a.round || b.round,
        stage: a.stage || b.stage,
        arena: a.arena || b.arena,
        stats: Map.merge(b.stats, a.stats)
    }
  end

  # ------------------------------------------------------------ cup finals

  # The Copa do Brasil files have no "final" marker. Where the cup file covers
  # a whole season its last round (two legs) is the final; otherwise the final
  # is inferred as the last tie of a season that is fully covered.
  defp label_cup_finals(matches) do
    {cup, rest} = Enum.split_with(matches, &(&1.competition == @cup))

    labelled =
      cup
      |> Enum.group_by(& &1.season)
      |> Enum.flat_map(fn {_season, ms} -> label_final(ms) end)

    labelled ++ rest
  end

  defp label_final(ms) do
    last = Enum.max_by(ms, &Date.to_gregorian_days(&1.date))
    numbered = Enum.filter(ms, &is_integer(&1.round))
    max_round = numbered |> Enum.map(& &1.round) |> Enum.max(fn -> nil end)
    last_round = Enum.filter(numbered, &(&1.round == max_round))

    final_ids =
      cond do
        last_round != [] and length(last_round) <= 2 and last.id in Enum.map(last_round, & &1.id) ->
          Enum.map(last_round, & &1.id)

        length(ms) >= 100 and last.date.month >= 9 ->
          ms
          |> Enum.filter(fn m ->
            Enum.sort([m.home, m.away]) == Enum.sort([last.home, last.away]) and
              Date.diff(last.date, m.date) <= 21
          end)
          |> Enum.map(& &1.id)

        true ->
          []
      end

    Enum.map(ms, fn m -> if m.id in final_ids, do: %{m | stage: "final"}, else: m end)
  end

  # ---------------------------------------------------------------- players

  defp to_player(r, teams, registry) do
    club = blank(r["Club"])

    %Player{
      id: Text.to_int(r["ID"]),
      name: r["Name"],
      age: Text.to_int(r["Age"]),
      nationality: r["Nationality"],
      overall: Text.to_int(r["Overall"]),
      potential: Text.to_int(r["Potential"]),
      club: club,
      club_key: club && club_key(club, teams, registry),
      position: blank(r["Position"]),
      jersey: Text.to_int(r["Jersey Number"]),
      height: blank(r["Height"]),
      weight: blank(r["Weight"]),
      foot: blank(r["Preferred Foot"]),
      value: blank(r["Value"]),
      wage: blank(r["Wage"]),
      attributes: for(c <- @attribute_columns, v = Text.to_int(r[c]), into: %{}, do: {c, v})
    }
  end

  # A FIFA club is linked to a match-data team only on an exact (or aliased)
  # name match, so "Boavista FC" (Portugal) is not confused with Boavista-RJ.
  defp club_key(club, teams, registry) do
    {base, state, label} = TeamNames.parse(club)
    k = key(registry, base, state)

    if Map.has_key?(teams, k) and
         (state != nil or TeamNames.clean(label) == base or TeamNames.alias?(club)), do: k
  end
end
