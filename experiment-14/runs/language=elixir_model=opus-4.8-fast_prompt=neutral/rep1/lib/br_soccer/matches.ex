defmodule BrSoccer.Matches do
  @moduledoc "Querying and filtering match records."

  alias BrSoccer.{Competition, Match, Repo, TeamName}

  @doc """
  Filter matches by any combination of criteria.

  Options:

    * `:team`        — club involved (home or away), by raw name
    * `:opponent`    — restrict to matches against this club
    * `:venue`       — `:home`, `:away` or `:either` (default `:either`) for `:team`
    * `:competition` — atom or free text (see `BrSoccer.Competition.parse/1`)
    * `:season`      — integer year
    * `:from`, `:to` — `Date`s (inclusive) bounding the match date
    * `:source`      — restrict to a single dataset source atom
    * `:scored_only` — drop matches without a recorded score (default `false`)
    * `:sort`        — `:date_desc` (default), `:date_asc`
    * `:limit`       — maximum number of results (after sorting)
  """
  def search(opts \\ []) do
    Repo.matches()
    |> filter(opts)
    |> sort(Keyword.get(opts, :sort, :date_desc))
    |> maybe_limit(Keyword.get(opts, :limit))
  end

  @doc "Same as `search/1` but returns `{matches, total_before_limit}`."
  def search_with_total(opts \\ []) do
    filtered =
      Repo.matches()
      |> filter(opts)
      |> sort(Keyword.get(opts, :sort, :date_desc))

    total = length(filtered)
    {maybe_limit(filtered, Keyword.get(opts, :limit)), total}
  end

  defp filter(matches, opts) do
    team_key = opts[:team] && TeamName.key(opts[:team])
    opp_key = opts[:opponent] && TeamName.key(opts[:opponent])
    venue = Keyword.get(opts, :venue, :either)
    comp = Competition.parse(opts[:competition])
    season = opts[:season]
    from = opts[:from]
    to = opts[:to]
    source = opts[:source]
    scored_only = Keyword.get(opts, :scored_only, false)

    Enum.filter(matches, fn m ->
      involves_team?(m, team_key, venue) and
        involves?(m, opp_key) and
        (is_nil(comp) or m.competition == comp) and
        (is_nil(season) or m.season == season) and
        (is_nil(source) or m.source == source) and
        date_in_range?(m.date, from, to) and
        (not scored_only or Match.scored?(m))
    end)
  end

  defp involves_team?(_m, nil, _venue), do: true
  defp involves_team?(m, key, :home), do: m.home_key == key
  defp involves_team?(m, key, :away), do: m.away_key == key
  defp involves_team?(m, key, _either), do: m.home_key == key or m.away_key == key

  defp involves?(_m, nil), do: true
  defp involves?(m, key), do: m.home_key == key or m.away_key == key

  defp date_in_range?(_date, nil, nil), do: true
  defp date_in_range?(nil, _from, _to), do: false

  defp date_in_range?(date, from, to) do
    (is_nil(from) or Date.compare(date, from) != :lt) and
      (is_nil(to) or Date.compare(date, to) != :gt)
  end

  @doc "Sort matches. Undated matches sort last for desc, first for asc... handled stably."
  def sort(matches, :date_asc), do: Enum.sort_by(matches, &sort_key/1)
  def sort(matches, :date_desc), do: Enum.sort_by(matches, &sort_key/1, :desc)
  def sort(matches, _), do: matches

  defp sort_key(%Match{date: %Date{} = d}), do: {Date.to_erl(d), 1}
  defp sort_key(%Match{season: s}) when is_integer(s), do: {{s, 0, 0}, 0}
  defp sort_key(_), do: {{0, 0, 0}, 0}

  defp maybe_limit(list, nil), do: list
  defp maybe_limit(list, n) when is_integer(n) and n >= 0, do: Enum.take(list, n)
  defp maybe_limit(list, _), do: list

  @doc """
  Head-to-head summary between two clubs.

  Returns a map with per-team win counts, draws, total goals and the list of
  matches (most recent first), optionally restricted by competition/season.
  """
  def head_to_head(team_a, team_b, opts \\ []) do
    key_a = TeamName.key(team_a)
    key_b = TeamName.key(team_b)

    matches =
      search(Keyword.merge(opts, team: team_a, opponent: team_b, scored_only: false))
      |> Enum.filter(&(involves?(&1, key_a) and involves?(&1, key_b)))

    scored = Enum.filter(matches, &Match.scored?/1)

    {a_wins, b_wins, draws, a_goals, b_goals} =
      Enum.reduce(scored, {0, 0, 0, 0, 0}, fn m, {aw, bw, d, ag, bg} ->
        {a_for, b_for} =
          if m.home_key == key_a,
            do: {m.home_goal, m.away_goal},
            else: {m.away_goal, m.home_goal}

        cond do
          a_for > b_for -> {aw + 1, bw, d, ag + a_for, bg + b_for}
          b_for > a_for -> {aw, bw + 1, d, ag + a_for, bg + b_for}
          true -> {aw, bw, d + 1, ag + a_for, bg + b_for}
        end
      end)

    %{
      team_a: display_for(matches, key_a, team_a),
      team_b: display_for(matches, key_b, team_b),
      key_a: key_a,
      key_b: key_b,
      total: length(matches),
      played: length(scored),
      a_wins: a_wins,
      b_wins: b_wins,
      draws: draws,
      a_goals: a_goals,
      b_goals: b_goals,
      matches: matches
    }
  end

  # Use a display name actually seen in the data when available.
  defp display_for(matches, key, fallback) do
    Enum.find_value(matches, TeamName.display(fallback), fn m ->
      cond do
        m.home_key == key -> m.home
        m.away_key == key -> m.away
        true -> nil
      end
    end)
  end

  @doc "The competitions a club has appeared in, with match counts."
  def competitions_for(team) do
    key = TeamName.key(team)

    Repo.matches()
    |> Enum.filter(&(&1.home_key == key or &1.away_key == key))
    |> Enum.group_by(& &1.competition)
    |> Enum.map(fn {comp, ms} ->
      seasons = ms |> Enum.map(& &1.season) |> Enum.reject(&is_nil/1) |> Enum.uniq() |> Enum.sort()
      %{competition: comp, matches: length(ms), seasons: seasons}
    end)
    |> Enum.sort_by(& &1.matches, :desc)
  end
end
