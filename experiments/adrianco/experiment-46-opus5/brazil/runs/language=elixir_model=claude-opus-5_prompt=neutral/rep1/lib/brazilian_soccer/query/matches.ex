defmodule BrazilianSoccer.Query.Matches do
  @moduledoc """
  Match search and head-to-head records.

  Every function takes the graph plus a plain map of arguments (string or atom
  keys, JSON friendly values) and returns `{:ok, result}` or `{:error, reason}`
  where `reason` is a tuple `BrazilianSoccer.Format` knows how to explain.
  """

  alias BrazilianSoccer.Data.Graph
  alias BrazilianSoccer.Model.Match
  alias BrazilianSoccer.Query.Filters

  @doc """
  Search matches.

  Arguments: `team`, `opponent`, `home_team`, `away_team`, `competition`,
  `season`, `season_from`, `season_to`, `date_from`, `date_to`, `stage`,
  `round`, `venue` (`home`/`away`/`all`, relative to `team`), `limit`.
  """
  @spec search(Graph.t(), map) :: {:ok, map} | {:error, tuple}
  def search(graph, args \\ %{}) do
    with {:ok, team} <- Filters.team(graph, Filters.get(args, :team)),
         {:ok, opponent} <- Filters.team(graph, Filters.get(args, :opponent)),
         {:ok, home} <- Filters.team(graph, Filters.get(args, :home_team)),
         {:ok, away} <- Filters.team(graph, Filters.get(args, :away_team)),
         {:ok, competition} <- Filters.competition(Filters.get(args, :competition)),
         {:ok, season} <- Filters.season(Filters.get(args, :season)),
         {:ok, season_from} <- Filters.season(Filters.get(args, :season_from)),
         {:ok, season_to} <- Filters.season(Filters.get(args, :season_to)),
         {:ok, date_from} <- Filters.date(Filters.get(args, :date_from)),
         {:ok, date_to} <- Filters.date(Filters.get(args, :date_to)),
         {:ok, venue} <- Filters.venue(Filters.get(args, :venue)) do
      limit = Filters.limit(Filters.get(args, :limit), 20)
      stage = Filters.get(args, :stage)
      round = Filters.integer(Filters.get(args, :round))

      candidates = candidate_matches(graph, [team, opponent, home, away], competition, season)

      matches =
        candidates
        |> Enum.filter(fn match ->
          involves?(match, team, venue) and
            involves?(match, opponent, :all) and
            side_is?(match, :home, home) and
            side_is?(match, :away, away) and
            (is_nil(competition) or match.competition == competition) and
            (is_nil(season) or match.season == season) and
            (is_nil(season_from) or (match.season || 0) >= season_from) and
            (is_nil(season_to) or (match.season || 9999) <= season_to) and
            after?(match.date, date_from) and
            before?(match.date, date_to) and
            stage_is?(match, stage) and
            (is_nil(round) or match.round == round)
        end)

      {:ok,
       %{
         matches: Enum.take(matches, limit),
         total: length(matches),
         limit: limit,
         filters:
           %{
             team: team && team.name,
             opponent: opponent && opponent.name,
             home_team: home && home.name,
             away_team: away && away.name,
             competition: competition,
             season: season,
             season_from: season_from,
             season_to: season_to,
             date_from: date_from,
             date_to: date_to,
             stage: stage,
             round: round,
             venue: venue
           }
           |> Map.reject(fn {_, v} -> is_nil(v) end)
       }}
    end
  end

  @doc """
  The most recent match between two teams (`nil` when they never met).
  """
  @spec last_meeting(Graph.t(), binary, binary) :: {:ok, map} | {:error, tuple}
  def last_meeting(graph, team_a, team_b) do
    with {:ok, result} <- search(graph, %{team: team_a, opponent: team_b, limit: 1}) do
      {:ok, Map.put(result, :match, List.first(result.matches))}
    end
  end

  @doc """
  Head-to-head record between two teams.

  Arguments: `team_a`, `team_b`, optional `competition`, `season`, `limit`
  (how many matches to list back).
  """
  @spec head_to_head(Graph.t(), map) :: {:ok, map} | {:error, tuple}
  def head_to_head(graph, args) do
    with {:ok, a} <- require_team(graph, Filters.get(args, :team_a) || Filters.get(args, :team)),
         {:ok, b} <-
           require_team(graph, Filters.get(args, :team_b) || Filters.get(args, :opponent)),
         {:ok, result} <-
           search(
             graph,
             args
             |> Map.new(fn {k, v} -> {k, v} end)
             |> Map.merge(%{
               team: a.id,
               opponent: b.id,
               team_a: nil,
               team_b: nil,
               # every meeting, so the record is a true one; the formatter
               # prints only the most recent of them
               limit: Filters.get(args, :limit) || :all
             })
           ) do
      matches = result.matches
      played = Enum.filter(matches, &Match.played?/1)

      summary =
        Enum.reduce(played, blank_h2h(), fn match, acc ->
          acc
          |> Map.update!(:matches, &(&1 + 1))
          |> Map.update!(:team_a_goals, &(&1 + Match.goals_for(match, a.id)))
          |> Map.update!(:team_b_goals, &(&1 + Match.goals_for(match, b.id)))
          |> then(fn acc ->
            case Match.outcome_for(match, a.id) do
              :win -> Map.update!(acc, :team_a_wins, &(&1 + 1))
              :loss -> Map.update!(acc, :team_b_wins, &(&1 + 1))
              :draw -> Map.update!(acc, :draws, &(&1 + 1))
              :unknown -> acc
            end
          end)
        end)

      by_competition =
        played
        |> Enum.group_by(& &1.competition)
        |> Map.new(fn {competition, list} ->
          {competition,
           %{
             matches: length(list),
             team_a_wins: Enum.count(list, &(Match.outcome_for(&1, a.id) == :win)),
             team_b_wins: Enum.count(list, &(Match.outcome_for(&1, b.id) == :win)),
             draws: Enum.count(list, &(Match.result(&1) == :draw))
           }}
        end)

      {:ok,
       %{
         team_a: a,
         team_b: b,
         matches: matches,
         summary: summary,
         by_competition: by_competition,
         first_meeting: List.last(played),
         last_meeting: List.first(played),
         filters: result.filters
       }}
    end
  end

  defp blank_h2h do
    %{matches: 0, team_a_wins: 0, team_b_wins: 0, draws: 0, team_a_goals: 0, team_b_goals: 0}
  end

  @doc """
  Matches between traditional rivals ("derbies"/"clássicos").

  Arguments: optional `team`, `season`, `competition`, `limit`.
  """
  @spec derbies(Graph.t(), map) :: {:ok, map} | {:error, tuple}
  def derbies(graph, args \\ %{}) do
    with {:ok, team} <- Filters.team(graph, Filters.get(args, :team)),
         {:ok, competition} <- Filters.competition(Filters.get(args, :competition)),
         {:ok, season} <- Filters.season(Filters.get(args, :season)) do
      limit = Filters.limit(Filters.get(args, :limit), 50)

      pairs =
        derby_pairs()
        |> Enum.map(fn {a, b, name} ->
          with {:ok, team_a} <- Graph.find_team(graph, a),
               {:ok, team_b} <- Graph.find_team(graph, b) do
            %{name: name, team_a: team_a, team_b: team_b}
          else
            _ -> nil
          end
        end)
        |> Enum.reject(&is_nil/1)
        |> Enum.filter(fn derby ->
          is_nil(team) or team.id in [derby.team_a.id, derby.team_b.id]
        end)

      derbies =
        Enum.map(pairs, fn derby ->
          {:ok, result} =
            search(graph, %{
              team: derby.team_a.id,
              opponent: derby.team_b.id,
              competition: competition,
              season: season,
              limit: limit
            })

          Map.merge(derby, %{matches: result.matches, total: result.total})
        end)
        |> Enum.filter(&(&1.total > 0))
        |> Enum.sort_by(& &1.name)

      {:ok,
       %{
         derbies: derbies,
         total_matches: Enum.sum(Enum.map(derbies, & &1.total)),
         filters:
           %{team: team && team.name, competition: competition, season: season}
           |> Map.reject(fn {_, v} -> is_nil(v) end)
       }}
    end
  end

  @doc "The traditional rivalries the server knows about."
  @spec derby_pairs() :: [{binary, binary, binary}]
  def derby_pairs do
    [
      {"Flamengo", "Fluminense", "Fla-Flu"},
      {"Flamengo", "Vasco da Gama", "Clássico dos Milhões"},
      {"Flamengo", "Botafogo", "Clássico da Rivalidade"},
      {"Botafogo", "Fluminense", "Clássico Vovô"},
      {"Vasco da Gama", "Botafogo", "Clássico da Amizade"},
      {"Fluminense", "Vasco da Gama", "Clássico dos Gigantes"},
      {"Corinthians", "Palmeiras", "Derby Paulista"},
      {"Corinthians", "São Paulo", "Majestoso"},
      {"Corinthians", "Santos", "Clássico Alvinegro"},
      {"Palmeiras", "São Paulo", "Choque-Rei"},
      {"Palmeiras", "Santos", "Clássico da Saudade"},
      {"Santos", "São Paulo", "San-São"},
      {"Grêmio", "Internacional", "Gre-Nal"},
      {"Atlético Mineiro", "Cruzeiro", "Clássico Mineiro"},
      {"Athletico Paranaense", "Coritiba", "Atletiba"},
      {"Bahia", "Vitória", "Ba-Vi"},
      {"Sport Recife", "Náutico", "Clássico dos Clássicos"},
      {"Sport Recife", "Santa Cruz", "Clássico das Multidões"},
      {"Ceará", "Fortaleza", "Clássico-Rei"},
      {"Goiás", "Atlético Goianiense", "Clássico Goianiense"}
    ]
  end

  # --- filter helpers ------------------------------------------------------

  # Narrow the candidate set using an index before filtering row by row.
  defp candidate_matches(graph, teams, competition, season) do
    case Enum.find(teams, & &1) do
      nil ->
        if competition,
          do: Graph.matches_for_competition(graph, competition, season),
          else: Graph.all_matches(graph)

      team ->
        Graph.matches_for_team(graph, team.id)
    end
  end

  defp involves?(_match, nil, _venue), do: true

  defp involves?(match, team, :all), do: team.id in [match.home_id, match.away_id]
  defp involves?(match, team, :home), do: match.home_id == team.id
  defp involves?(match, team, :away), do: match.away_id == team.id

  defp side_is?(_match, _side, nil), do: true
  defp side_is?(match, :home, team), do: match.home_id == team.id
  defp side_is?(match, :away, team), do: match.away_id == team.id

  defp after?(_date, nil), do: true
  defp after?(nil, _from), do: false
  defp after?(date, from), do: Date.compare(date, from) != :lt

  defp before?(_date, nil), do: true
  defp before?(nil, _to), do: false
  defp before?(date, to), do: Date.compare(date, to) != :gt

  defp stage_is?(_match, nil), do: true
  defp stage_is?(_match, ""), do: true

  defp stage_is?(%Match{stage: nil}, stage) when is_binary(stage), do: false

  defp stage_is?(match, stage) when is_binary(stage) do
    wanted = normalise_stage(stage)
    actual = normalise_stage(match.stage)

    # `starts_with?` lets "round" match "round of 16" without letting
    # "final" match "semifinal" or "quarterfinal".
    actual == wanted or String.starts_with?(actual, wanted)
  end

  defp normalise_stage(stage) do
    stage
    |> BrazilianSoccer.Names.ascii()
    |> String.downcase()
    |> String.replace(~r/[^a-z0-9]/u, "")
    |> String.replace(~r/s$/u, "")
  end

  defp require_team(_graph, nil), do: {:error, {:missing_argument, :team_a}}
  defp require_team(graph, name), do: Graph.find_team(graph, name)
end
