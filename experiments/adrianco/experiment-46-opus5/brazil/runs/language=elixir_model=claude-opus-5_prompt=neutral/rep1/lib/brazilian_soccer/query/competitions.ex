defmodule BrazilianSoccer.Query.Competitions do
  @moduledoc """
  Competition level queries: league tables computed from match results, cup
  brackets, champions and per-season summaries.

  Nothing in the datasets records who lifted the trophy, so champions are
  derived: the top of a computed league table, or the winner of the final for
  the cups (on aggregate over the two legs when there are two).
  """

  alias BrazilianSoccer.Data.Graph
  alias BrazilianSoccer.Model.Match
  alias BrazilianSoccer.Query.{Filters, Teams}

  @relegation_spots 4
  @stage_order ["group stage", "round of 16", "quarterfinals", "semifinals", "final"]

  @doc "Every competition with its seasons and match counts."
  @spec list(Graph.t()) :: {:ok, map}
  def list(graph) do
    competitions =
      Graph.competitions()
      |> Enum.map(fn competition ->
        seasons = Graph.seasons(graph, competition.id)
        matches = Graph.matches_for_competition(graph, competition.id)

        %{
          competition: competition,
          seasons: seasons,
          season_range: season_range(seasons),
          matches: length(matches),
          teams:
            matches
            |> Enum.flat_map(&[&1.home_id, &1.away_id])
            |> Enum.uniq()
            |> length()
        }
      end)
      |> Enum.filter(&(&1.matches > 0))

    {:ok, %{competitions: competitions}}
  end

  @doc """
  League table for a competition season, computed from match results.

  Arguments: `competition` (default Série A), `season` (required),
  `venue` (`home`/`away`/`all`) to build home-only or away-only tables.
  """
  @spec standings(Graph.t(), map) :: {:ok, map} | {:error, tuple}
  def standings(graph, args) do
    with {:ok, competition} <- competition(args),
         {:ok, season} <- require_season(args),
         {:ok, venue} <- Filters.venue(Filters.get(args, :venue)) do
      matches =
        graph
        |> Graph.matches_for_competition(competition, season)
        |> Enum.filter(&Match.played?/1)

      case matches do
        [] ->
          {:error, {:no_data, competition, season, Graph.seasons(graph, competition)}}

        _ ->
          league? = competition in Graph.leagues()
          {table, dropped} = build_table(graph, matches, venue) |> drop_outliers(league?)

          {:ok,
           %{
             dropped_teams: dropped,
             competition: Graph.competition(competition),
             season: season,
             venue: venue,
             table: table,
             matches_counted: length(matches),
             expected_matches: expected_matches(table, league?),
             champion: if(league? and venue == :all, do: table |> List.first() |> Map.get(:team)),
             relegated: relegated(table, league?, venue),
             note:
               [note(competition, league?), completeness_note(table, matches, league?, venue)]
               |> Enum.filter(& &1)
               |> Enum.join(" ")
           }}
      end
    end
  end

  @doc """
  Who won a competition in a season.

  Leagues: top of the computed table.  Cups: winner of the final, on aggregate
  when the final was played over two legs.
  """
  @spec champion(Graph.t(), map) :: {:ok, map} | {:error, tuple}
  def champion(graph, args) do
    with {:ok, competition} <- competition(args),
         {:ok, season} <- require_season(args) do
      if competition in Graph.leagues() do
        with {:ok, standings} <- standings(graph, args) do
          [leader | _] = standings.table

          {:ok,
           %{
             competition: standings.competition,
             season: season,
             champion: leader.team,
             basis: :league_table,
             detail: leader,
             runner_up: standings.table |> Enum.at(1) |> then(&(&1 && &1.team)),
             note: standings.note
           }}
        end
      else
        cup_champion(graph, competition, season)
      end
    end
  end

  defp cup_champion(graph, competition, season) do
    final =
      graph
      |> Graph.matches_for_competition(competition, season)
      |> Enum.filter(&(&1.stage != nil and String.downcase(&1.stage) == "final"))

    case final do
      [] ->
        {:error, {:no_final, competition, season, Graph.seasons(graph, competition)}}

      legs ->
        {winner, detail} = decide_final(graph, legs)

        {:ok,
         %{
           competition: Graph.competition(competition),
           season: season,
           champion: winner,
           basis: :final,
           detail: detail,
           runner_up: detail[:runner_up],
           note:
             "Champion derived from the final#{if length(legs) > 1, do: " (#{length(legs)} legs, on aggregate)", else: ""}; penalty shoot-outs are not in the data."
         }}
    end
  end

  defp decide_final(graph, legs) do
    aggregate =
      Enum.reduce(legs, %{}, fn match, acc ->
        acc
        |> Map.update(match.home_id, match.home_goals || 0, &(&1 + (match.home_goals || 0)))
        |> Map.update(match.away_id, match.away_goals || 0, &(&1 + (match.away_goals || 0)))
      end)

    played? = Enum.all?(legs, &Match.played?/1)

    case aggregate |> Enum.sort_by(fn {_, goals} -> -goals end) do
      [{winner_id, winner_goals}, {loser_id, loser_goals} | _] when played? ->
        if winner_goals == loser_goals do
          {nil,
           %{
             legs: legs,
             aggregate: aggregate,
             undecided: true,
             finalists: Enum.map([winner_id, loser_id], &Graph.team(graph, &1))
           }}
        else
          {Graph.team(graph, winner_id),
           %{
             legs: legs,
             aggregate: aggregate,
             runner_up: Graph.team(graph, loser_id)
           }}
        end

      _ ->
        {nil, %{legs: legs, aggregate: aggregate, undecided: true}}
    end
  end

  @doc """
  Cup bracket / stage breakdown for a season.
  """
  @spec bracket(Graph.t(), map) :: {:ok, map} | {:error, tuple}
  def bracket(graph, args) do
    with {:ok, competition} <- competition(args),
         {:ok, season} <- require_season(args) do
      matches = Graph.matches_for_competition(graph, competition, season)

      case matches do
        [] ->
          {:error, {:no_data, competition, season, Graph.seasons(graph, competition)}}

        _ ->
          stages =
            matches
            |> Enum.group_by(&(&1.stage || "unknown stage"))
            |> Enum.sort_by(fn {stage, _} -> stage_rank(stage) end)
            |> Enum.map(fn {stage, list} ->
              %{stage: stage, matches: Enum.sort_by(list, &sort_date/1)}
            end)

          champion =
            case cup_champion(graph, competition, season) do
              {:ok, result} -> result
              {:error, _} -> nil
            end

          {:ok,
           %{
             competition: Graph.competition(competition),
             season: season,
             stages: stages,
             champion: champion,
             matches_counted: length(matches)
           }}
      end
    end
  end

  @doc """
  Summary of a competition season: goals, home advantage, top scorers by team,
  biggest win and (derived) champion.
  """
  @spec summary(Graph.t(), map) :: {:ok, map} | {:error, tuple}
  def summary(graph, args) do
    with {:ok, competition} <- competition(args),
         {:ok, season} <- Filters.season(Filters.get(args, :season)) do
      matches =
        graph
        |> Graph.matches_for_competition(competition, season)
        |> Enum.filter(&Match.played?/1)

      case matches do
        [] ->
          {:error, {:no_data, competition, season, Graph.seasons(graph, competition)}}

        _ ->
          teams =
            matches
            |> Enum.flat_map(&[&1.home_id, &1.away_id])
            |> Enum.uniq()

          scoring =
            teams
            |> Enum.map(fn team_id ->
              relevant = Enum.filter(matches, &(team_id in [&1.home_id, &1.away_id]))
              %{team: Graph.team(graph, team_id), record: Teams.record(relevant, team_id)}
            end)
            |> Enum.sort_by(&(-&1.record.goals_for))

          champion =
            if season do
              case champion(graph, %{competition: competition, season: season}) do
                {:ok, result} -> result
                {:error, _} -> nil
              end
            end

          {:ok,
           %{
             competition: Graph.competition(competition),
             season: season,
             seasons: Graph.seasons(graph, competition),
             matches: length(matches),
             teams: length(teams),
             goals: Enum.sum(Enum.map(matches, &Match.total_goals/1)),
             goals_per_match: goals_per_match(matches),
             home_win_rate: rate(matches, :home_win),
             draw_rate: rate(matches, :draw),
             away_win_rate: rate(matches, :away_win),
             top_scoring_teams: Enum.take(scoring, 5),
             best_defences: scoring |> Enum.sort_by(& &1.record.goals_against) |> Enum.take(5),
             biggest_win: Enum.max_by(matches, &Match.margin/1, fn -> nil end),
             champion: champion
           }}
      end
    end
  end

  # --- helpers -------------------------------------------------------------

  defp build_table(graph, matches, venue) do
    matches
    |> Enum.flat_map(&[&1.home_id, &1.away_id])
    |> Enum.uniq()
    |> Enum.map(fn team_id ->
      relevant =
        Enum.filter(matches, fn match ->
          case venue do
            :home -> match.home_id == team_id
            :away -> match.away_id == team_id
            :all -> team_id in [match.home_id, match.away_id]
          end
        end)

      %{team: Graph.team(graph, team_id), record: Teams.record(relevant, team_id)}
    end)
    |> Enum.filter(&(&1.record.matches > 0))
    |> Enum.sort_by(fn %{record: r} ->
      {-r.points, -r.wins, -r.goal_difference, -r.goals_for}
    end)
    |> Enum.with_index(1)
    |> Enum.map(fn {row, position} -> Map.put(row, :position, position) end)
  end

  # A handful of rows in `BR-Football-Dataset.csv` are mislabelled (a state
  # championship tagged "Serie A", say).  In a league every club plays the same
  # number of games, so a club with a fraction of the fixtures did not really
  # take part and would otherwise pollute the table.
  defp drop_outliers(table, false), do: {table, []}
  defp drop_outliers([], _league?), do: {[], []}

  defp drop_outliers(table, true) do
    threshold = table |> Enum.map(& &1.record.matches) |> Enum.max() |> div(2)
    {kept, dropped} = Enum.split_with(table, &(&1.record.matches >= threshold))

    kept =
      kept
      |> Enum.with_index(1)
      |> Enum.map(fn {row, position} -> Map.put(row, :position, position) end)

    {kept, Enum.map(dropped, & &1.team)}
  end

  defp relegated(table, true, :all) when length(table) >= 12 do
    table |> Enum.take(-@relegation_spots) |> Enum.map(& &1.team)
  end

  defp relegated(_table, _league?, _venue), do: []

  defp note(_competition, true) do
    "Table computed from the match results in the dataset (3 points per win); " <>
      "points deductions and other sanctions are not represented."
  end

  defp note(_competition, false) do
    "Knock-out competition: the table is not an official standing."
  end

  # A double round-robin of n clubs is n * (n - 1) matches; anything less means
  # the source files are missing fixtures, and the table may then disagree with
  # the official one.
  defp expected_matches(table, true), do: length(table) * (length(table) - 1)
  defp expected_matches(_table, false), do: nil

  defp completeness_note(table, matches, true, :all) do
    expected = expected_matches(table, true)

    if expected > 0 and length(matches) < expected do
      "Careful: the datasets hold #{length(matches)} of the #{expected} matches this season needs, " <>
        "so the placings can differ from the official table."
    end
  end

  defp completeness_note(_table, _matches, _league?, _venue), do: nil

  defp competition(args) do
    case Filters.get(args, :competition) do
      nil -> {:ok, :serie_a}
      value -> Filters.competition(value)
    end
  end

  defp require_season(args) do
    case Filters.season(Filters.get(args, :season)) do
      {:ok, nil} -> {:error, {:missing_argument, :season}}
      other -> other
    end
  end

  defp season_range([]), do: nil
  defp season_range(seasons), do: {Enum.min(seasons), Enum.max(seasons)}

  defp stage_rank(stage) do
    normalised = String.downcase(stage)

    case Enum.find_index(@stage_order, &(&1 == normalised)) do
      nil -> 50
      index -> index
    end
  end

  defp sort_date(%Match{date: nil}), do: ~D[1900-01-01]
  defp sort_date(%Match{date: date}), do: date

  defp goals_per_match(matches) do
    Float.round(Enum.sum(Enum.map(matches, &Match.total_goals/1)) / length(matches), 2)
  end

  defp rate(matches, result) do
    Float.round(Enum.count(matches, &(Match.result(&1) == result)) * 100 / length(matches), 1)
  end
end
