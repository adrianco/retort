defmodule BrazilianSoccerMcp.Queries do
  @moduledoc """
  Pure query functions over loaded matches and players.

  Match filters, passed as keyword options (all optional):

    * `:competition` - key or friendly name, see `Competition.canonical/1`
    * `:season` - integer year
    * `:venue` - `:home`, `:away` or `:any` (team-centric queries only)
    * `:date_from` / `:date_to` - inclusive `Date` bounds
    * `:limit` - maximum rows returned
  """

  alias BrazilianSoccerMcp.{Competition, Match, Player, TeamName}

  @default_limit 20
  @default_standings_competition "brasileirao"

  ## Team resolution

  @doc """
  Resolves a free-text team name to a team key, or `nil`.

  A name with a state suffix (`"Atletico-MG"`) selects that club. A bare name
  matches every key with that base, and the most frequent one wins. If no base
  matches, a substring match is tried, so `"Fla"` finds `"flamengo"`.
  """
  @spec resolve_team([Match.t()], binary() | nil) :: binary() | nil
  def resolve_team(matches, query) when is_binary(query) do
    {base, state} = TeamName.parse(query)
    counts = team_counts(matches)

    candidates =
      counts
      |> Map.keys()
      |> Enum.filter(
        &(TeamName.base(&1) == base and (is_nil(state) or TeamName.state(&1) == state))
      )

    candidates =
      if candidates == [] and base != "" do
        Enum.filter(Map.keys(counts), &String.contains?(TeamName.base(&1), base))
      else
        candidates
      end

    case candidates do
      [] -> nil
      _ -> Enum.max_by(candidates, &Map.fetch!(counts, &1))
    end
  end

  def resolve_team(_matches, _query), do: nil

  @doc "How many match appearances each team key has."
  @spec team_counts([Match.t()]) :: %{binary() => pos_integer()}
  def team_counts(matches) do
    matches |> Enum.flat_map(&[&1.home_key, &1.away_key]) |> Enum.frequencies()
  end

  @doc "Readable name for a team key, taken from the first match that uses it."
  @spec team_name([Match.t()], binary()) :: binary() | nil
  def team_name(matches, key) do
    Enum.find_value(matches, key, fn
      %Match{home_key: ^key, home: name} -> name
      %Match{away_key: ^key, away: name} -> name
      _ -> nil
    end)
  end

  # Readable name for a base key, used when a player's club is not state-qualified.
  defp base_name(matches, base) do
    Enum.find_value(matches, base, fn m ->
      cond do
        TeamName.base(m.home_key) == base -> m.home
        TeamName.base(m.away_key) == base -> m.away
        true -> nil
      end
    end)
  end

  ## Filtering

  @doc "Keeps matches satisfying the competition, season and date options."
  @spec filter([Match.t()], keyword()) :: [Match.t()]
  def filter(matches, opts \\ []) do
    competition = Competition.canonical(opts[:competition])

    Enum.filter(matches, fn m ->
      (is_nil(competition) or m.competition == competition) and
        (is_nil(opts[:season]) or m.season == opts[:season]) and
        (is_nil(opts[:date_from]) or Date.compare(m.date, opts[:date_from]) != :lt) and
        (is_nil(opts[:date_to]) or Date.compare(m.date, opts[:date_to]) != :gt)
    end)
  end

  @doc "Matches played by `key`, restricted to home, away or any venue."
  @spec team_matches([Match.t()], binary(), :home | :away | :any) :: [Match.t()]
  def team_matches(matches, key, venue \\ :any) do
    Enum.filter(matches, &at_venue?(&1, key, venue))
  end

  ## Match search

  @doc """
  Finds matches by team, opponent or both, most recent first.

  Returns `{:ok, %{total: n, matches: [...]}}`, where `matches` is limited to
  `:limit`, or `{:error, message}` for an unknown team name.
  """
  @spec search_matches([Match.t()], keyword()) :: {:ok, map()} | {:error, binary()}
  def search_matches(matches, opts \\ []) do
    with {:ok, team} <- resolve_optional(matches, opts[:team]),
         {:ok, opponent} <- resolve_optional(matches, opts[:opponent]) do
      venue = Keyword.get(opts, :venue, :any)

      found =
        matches
        |> filter(opts)
        |> Enum.filter(&involves?(&1, team, opponent, venue))
        |> sort_recent()

      {:ok, %{total: length(found), matches: Enum.take(found, limit(opts))}}
    end
  end

  @doc """
  Head-to-head record between two teams, from `team_a`'s point of view.

  Returns `{:ok, map}` with `:matches`, `:a_wins`, `:b_wins`, `:draws`,
  `:a_goals`, `:b_goals` and `:recent` (up to `:limit` meetings, newest first).
  """
  @spec head_to_head([Match.t()], binary(), binary(), keyword()) ::
          {:ok, map()} | {:error, binary()}
  def head_to_head(matches, team_a, team_b, opts \\ []) do
    with {:ok, a} <- required_team(matches, team_a),
         {:ok, b} <- required_team(matches, team_b),
         :ok <- distinct(a, b) do
      meetings =
        matches
        |> filter(opts)
        |> Enum.filter(&meets?(&1, a, b, :any))
        |> sort_recent()

      a_wins = Enum.count(meetings, &(goals_for(&1, a) > goals_for(&1, b)))
      draws = Enum.count(meetings, &(goals_for(&1, a) == goals_for(&1, b)))

      {:ok,
       %{
         team_a: team_name(matches, a),
         team_b: team_name(matches, b),
         matches: length(meetings),
         a_wins: a_wins,
         b_wins: length(meetings) - a_wins - draws,
         draws: draws,
         a_goals: sum_goals(meetings, a),
         b_goals: sum_goals(meetings, b),
         recent: Enum.take(meetings, limit(opts))
       }}
    end
  end

  ## Team records and tables

  @doc """
  Win/draw/loss record and goals for one team.

  Returns `{:ok, stats}` where `stats` has the fields described in `tally/2`
  plus `:gd`, `:points` and `:win_rate`, or `{:error, message}` if the team is unknown.
  """
  @spec team_record([Match.t()], binary(), keyword()) :: {:ok, map()} | {:error, binary()}
  def team_record(matches, team, opts \\ []) do
    case resolve_team(matches, team) do
      nil ->
        {:error, "Unknown team: #{team}"}

      key ->
        venue = Keyword.get(opts, :venue, :any)

        stats =
          matches
          |> filter(opts)
          |> team_matches(key, venue)
          |> tally(venue)
          |> Map.get(key, new_stats(key, team_name(matches, key)))

        {:ok, finalize(stats)}
    end
  end

  @doc """
  Groups matches into per-team totals.

  Each entry has `:key`, `:team`, `:played`, `:wins`, `:draws`, `:losses`, `:gf`
  and `:ga`. Only the chosen venue side is counted for each match.
  """
  @spec tally([Match.t()], :home | :away | :any) :: %{binary() => map()}
  def tally(matches, venue \\ :any) do
    Enum.reduce(matches, %{}, fn m, acc ->
      acc
      |> add_side(m, :home, venue)
      |> add_side(m, :away, venue)
    end)
  end

  @doc """
  League table for one season, sorted by points, wins, goal difference, goals scored, then name.

  Defaults to the Brasileirão Série A. Returns `{:error, message}` without a season.
  """
  @spec standings([Match.t()], keyword()) :: {:ok, [map()]} | {:error, binary()}
  def standings(matches, opts \\ []) do
    if is_nil(opts[:season]) do
      {:error, "standings requires a season"}
    else
      opts = Keyword.put_new(opts, :competition, @default_standings_competition)

      table =
        matches
        |> filter(opts)
        |> tally()
        |> Map.values()
        |> Enum.map(&finalize/1)
        |> Enum.sort_by(&{-&1.points, -&1.wins, -&1.gd, -&1.gf, &1.team})

      {:ok, table}
    end
  end

  @doc "Teams ranked by `:metric` (`:win_rate`, `:wins` or `:gf`), with at least `:min_matches` games."
  @spec team_rankings([Match.t()], keyword()) :: {:ok, [map()]}
  def team_rankings(matches, opts \\ []) do
    metric = Keyword.get(opts, :metric, :win_rate)
    min_matches = Keyword.get(opts, :min_matches, 10)
    venue = Keyword.get(opts, :venue, :any)

    rows =
      matches
      |> filter(opts)
      |> tally(venue)
      |> Map.values()
      |> Enum.map(&finalize/1)
      |> Enum.filter(&(&1.played >= min_matches))
      |> Enum.sort_by(&{Map.fetch!(&1, metric), &1.played}, :desc)

    {:ok, Enum.take(rows, limit(opts, 10))}
  end

  ## League statistics

  @doc """
  Aggregate statistics: match count, goals per match, and home, draw and away rates.

  Returns `{:error, message}` when no matches fit the filters.
  """
  @spec league_stats([Match.t()], keyword()) :: {:ok, map()} | {:error, binary()}
  def league_stats(matches, opts \\ []) do
    found = filter(matches, opts)
    total = length(found)

    if total == 0 do
      {:error, "No matches found for those filters"}
    else
      home_wins = Enum.count(found, &(&1.home_goals > &1.away_goals))
      draws = Enum.count(found, &(&1.home_goals == &1.away_goals))
      goals = Enum.sum(Enum.map(found, &(&1.home_goals + &1.away_goals)))

      {:ok,
       %{
         matches: total,
         goals_per_match: Float.round(goals / total, 2),
         home_win_rate: percent(home_wins, total),
         draw_rate: percent(draws, total),
         away_win_rate: percent(total - home_wins - draws, total)
       }}
    end
  end

  @doc "Decisive matches with the largest winning margin, largest first."
  @spec biggest_wins([Match.t()], keyword()) :: {:ok, [Match.t()]}
  def biggest_wins(matches, opts \\ []) do
    wins =
      matches
      |> filter(opts)
      |> Enum.reject(&(&1.home_goals == &1.away_goals))
      |> Enum.sort_by(&{margin(&1), Date.to_iso8601(&1.date)}, :desc)

    {:ok, Enum.take(wins, limit(opts, 10))}
  end

  ## Players

  @doc """
  Searches players by name, nationality, club, position or minimum overall.

  Name and club are substring matches on normalized text. Nationality and
  position must match exactly (case-insensitive). Sorted by overall, then name.
  """
  @spec search_players([Player.t()], keyword()) :: {:ok, [Player.t()]}
  def search_players(players, opts \\ []) do
    name = opts[:name] && TeamName.normalize(opts[:name])
    nationality = opts[:nationality] && TeamName.normalize(opts[:nationality])
    club = opts[:club] && TeamName.key(opts[:club])
    position = opts[:position] && String.upcase(opts[:position])
    min_overall = opts[:min_overall] || 0

    found =
      Enum.filter(players, fn p ->
        (is_nil(name) or String.contains?(p.name_key, name)) and
          (is_nil(nationality) or p.nationality_key == nationality) and
          (is_nil(club) or padded_contains?(p.club_key, club)) and
          (is_nil(position) or p.position == position) and
          p.overall >= min_overall
      end)

    {:ok, found |> Enum.sort_by(&{-&1.overall, &1.name}) |> Enum.take(limit(opts))}
  end

  @doc """
  Groups players of a nationality (default `"Brazil"`) by clubs that appear in the match data.

  Each entry has `:club`, `:squad_size`, `:avg_overall` and `:best`, the highest-rated player.
  """
  @spec club_summary([Player.t()], [Match.t()], keyword()) :: {:ok, [map()]}
  def club_summary(players, matches, opts \\ []) do
    nationality = TeamName.normalize(Keyword.get(opts, :nationality, "Brazil"))

    club_bases =
      matches |> team_counts() |> Map.keys() |> Enum.map(&TeamName.base/1) |> MapSet.new()

    rows =
      players
      |> Enum.filter(
        &(&1.nationality_key == nationality and MapSet.member?(club_bases, &1.club_key))
      )
      |> Enum.group_by(& &1.club_key)
      |> Enum.map(fn {base, squad} ->
        %{
          club: base_name(matches, base),
          squad_size: length(squad),
          avg_overall: average(squad),
          best: Enum.min_by(squad, &{-&1.overall, &1.name})
        }
      end)
      |> Enum.sort_by(&{-&1.squad_size, &1.club})

    {:ok, Enum.take(rows, limit(opts, 10))}
  end

  @doc """
  Cross-file view of one team: its match record plus the FIFA squad whose club maps to the same key.

  Returns `{:ok, %{record: stats, squad_size: n, avg_overall: float | nil, top: [Player.t()]}}`
  with the five highest-rated players in `:top`.
  """
  @spec team_overview([Match.t()], [Player.t()], binary()) :: {:ok, map()} | {:error, binary()}
  def team_overview(matches, players, team) do
    with {:ok, record} <- team_record(matches, team) do
      base = TeamName.base(record.key)
      squad = Enum.filter(players, &(&1.club_key == base))

      {:ok,
       %{
         record: record,
         squad_size: length(squad),
         avg_overall: average(squad),
         top: squad |> Enum.sort_by(&{-&1.overall, &1.name}) |> Enum.take(5)
       }}
    end
  end

  ## Internal helpers

  defp resolve_optional(_matches, nil), do: {:ok, nil}

  defp resolve_optional(matches, name) do
    case resolve_team(matches, name) do
      nil -> {:error, "Unknown team: #{name}"}
      key -> {:ok, key}
    end
  end

  defp required_team(matches, name) do
    case resolve_team(matches, name) do
      nil -> {:error, "Unknown team: #{name}"}
      key -> {:ok, key}
    end
  end

  defp distinct(a, a), do: {:error, "Team A and team B must be different"}
  defp distinct(_a, _b), do: :ok

  defp at_venue?(m, key, venue) do
    (venue != :away and m.home_key == key) or (venue != :home and m.away_key == key)
  end

  defp involves?(_m, nil, nil, _venue), do: true
  defp involves?(m, team, nil, venue), do: at_venue?(m, team, venue)
  defp involves?(m, nil, opponent, venue), do: at_venue?(m, opponent, venue)
  defp involves?(m, team, opponent, venue), do: meets?(m, team, opponent, venue)

  defp meets?(m, team, opponent, venue) do
    (venue != :away and m.home_key == team and m.away_key == opponent) or
      (venue != :home and m.home_key == opponent and m.away_key == team)
  end

  defp add_side(acc, m, side, venue) do
    if venue == :any or venue == side do
      {key, name, gf, ga} =
        case side do
          :home -> {m.home_key, m.home, m.home_goals, m.away_goals}
          :away -> {m.away_key, m.away, m.away_goals, m.home_goals}
        end

      stats = Map.get(acc, key, new_stats(key, name))
      Map.put(acc, key, record(stats, gf, ga))
    else
      acc
    end
  end

  defp new_stats(key, name) do
    %{key: key, team: name, played: 0, wins: 0, draws: 0, losses: 0, gf: 0, ga: 0}
  end

  defp record(stats, gf, ga) do
    outcome =
      cond do
        gf > ga -> :wins
        gf == ga -> :draws
        true -> :losses
      end

    stats
    |> Map.update!(:played, &(&1 + 1))
    |> Map.update!(:gf, &(&1 + gf))
    |> Map.update!(:ga, &(&1 + ga))
    |> Map.update!(outcome, &(&1 + 1))
  end

  defp finalize(stats) do
    Map.merge(stats, %{
      gd: stats.gf - stats.ga,
      points: 3 * stats.wins + stats.draws,
      win_rate: percent(stats.wins, stats.played)
    })
  end

  defp goals_for(m, key), do: if(m.home_key == key, do: m.home_goals, else: m.away_goals)

  defp sum_goals(matches, key), do: Enum.sum(Enum.map(matches, &goals_for(&1, key)))

  defp margin(m), do: abs(m.home_goals - m.away_goals)

  defp sort_recent(matches), do: Enum.sort_by(matches, & &1.date, {:desc, Date})

  defp limit(opts, default \\ @default_limit), do: Keyword.get(opts, :limit) || default

  defp percent(_part, 0), do: 0.0
  defp percent(part, whole), do: Float.round(part * 100 / whole, 1)

  defp average([]), do: nil

  defp average(players),
    do: Float.round(Enum.sum(Enum.map(players, & &1.overall)) / length(players), 1)

  defp padded_contains?(nil, _needle), do: false
  defp padded_contains?(text, needle), do: String.contains?(" #{text} ", " #{needle} ")
end
