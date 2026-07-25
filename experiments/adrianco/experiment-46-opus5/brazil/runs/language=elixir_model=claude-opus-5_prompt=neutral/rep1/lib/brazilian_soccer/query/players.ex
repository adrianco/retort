defmodule BrazilianSoccer.Query.Players do
  @moduledoc """
  Player queries over the FIFA database, plus the cross-dataset link between a
  player's club and the match knowledge graph.

  Heads up on data coverage: the FIFA 19 export does not license every
  Brazilian club, so Flamengo, Palmeiras, Corinthians, São Paulo and Vasco have
  no players in it while Grêmio, Cruzeiro, Santos, Fluminense and friends do.
  `club_squad/2` says so explicitly instead of pretending the club is unknown.
  """

  alias BrazilianSoccer.Data.Graph
  alias BrazilianSoccer.Model.Player
  alias BrazilianSoccer.Names
  alias BrazilianSoccer.Query.Filters

  @doc """
  Search players.

  Arguments: `name`, `nationality`, `club`, `position`, `position_group`
  (`forward`/`midfielder`/`defender`/`goalkeeper`), `min_overall`,
  `max_overall`, `min_age`, `max_age`, `brazilian_clubs_only`, `sort_by`
  (`overall`/`potential`/`age`/`value`/`name`), `limit`.
  """
  @spec search(Graph.t(), map) :: {:ok, map} | {:error, tuple}
  def search(graph, args \\ %{}) do
    name = Filters.get(args, :name)
    nationality = Filters.get(args, :nationality)
    club = Filters.get(args, :club)
    position = Filters.get(args, :position)
    group = position_group(Filters.get(args, :position_group))
    min_overall = Filters.integer(Filters.get(args, :min_overall))
    max_overall = Filters.integer(Filters.get(args, :max_overall))
    min_age = Filters.integer(Filters.get(args, :min_age))
    max_age = Filters.integer(Filters.get(args, :max_age))
    brazilian_only = Filters.boolean(Filters.get(args, :brazilian_clubs_only), false)
    limit = Filters.limit(Filters.get(args, :limit), 20)
    sort_by = sort_key(Filters.get(args, :sort_by))

    club_team =
      case club do
        nil -> nil
        "" -> nil
        value -> Graph.find_teams(graph, value, 1) |> List.first()
      end

    # When the club resolves to a club that really has players, match on the
    # graph link only.  Falling back to substrings here would let "Santos"
    # drag in Santos Laguna of Mexico.
    club_filter =
      cond do
        is_nil(club) or club == "" ->
          :any

        is_nil(club_team) ->
          {:name, normalise(club)}

        Map.has_key?(graph.players_by_club, club_team.id) and same_club?(club, club_team) ->
          {:club_id, club_team.id}

        true ->
          {:name, normalise(club)}
      end

    name_key = name && normalise(name)
    nationality_key = nationality && normalise(nationality)
    position_key = position && String.upcase(String.trim(position))

    players =
      graph.players
      |> Map.values()
      |> Enum.filter(fn player ->
        matches_name?(player, name_key) and
          matches_nationality?(player, nationality_key) and
          matches_club?(player, club_filter) and
          (is_nil(position_key) or player.position == position_key) and
          (is_nil(group) or Player.position_group(player) == group) and
          (is_nil(min_overall) or (player.overall || 0) >= min_overall) and
          (is_nil(max_overall) or (player.overall || 0) <= max_overall) and
          (is_nil(min_age) or (player.age || 0) >= min_age) and
          (is_nil(max_age) or (player.age || 999) <= max_age) and
          (not brazilian_only or player.club_id != nil)
      end)
      |> Enum.sort_by(&sort_value(&1, sort_by))

    {:ok,
     %{
       players: Enum.take(players, limit),
       total: length(players),
       limit: limit,
       sort_by: sort_by,
       filters:
         %{
           name: name,
           nationality: nationality,
           club: club_team && club_team.name,
           club_query: club,
           position: position_key,
           position_group: group,
           min_overall: min_overall,
           max_overall: max_overall,
           min_age: min_age,
           max_age: max_age,
           brazilian_clubs_only: brazilian_only
         }
         |> Map.reject(fn {_, v} -> is_nil(v) or v == false end)
     }}
  end

  @doc """
  A single player with their club link into the match graph.

  Arguments: `name` or `player_id`.
  """
  @spec profile(Graph.t(), map) :: {:ok, map} | {:error, tuple}
  def profile(graph, args) do
    id = Filters.integer(Filters.get(args, :player_id))
    name = Filters.get(args, :name)

    player =
      cond do
        id -> Graph.player(graph, id)
        is_binary(name) -> best_name_match(graph, name)
        true -> nil
      end

    case player do
      nil when is_binary(name) ->
        {:error, {:player_not_found, name, name_suggestions(graph, name)}}

      nil ->
        {:error, {:missing_argument, :name}}

      player ->
        club_team = player.club_id && Graph.team(graph, player.club_id)

        club_matches =
          if club_team, do: Enum.take(Graph.matches_for_team(graph, club_team.id), 5), else: []

        teammates =
          if club_team do
            graph
            |> Graph.players_for_club(club_team.id)
            |> Enum.reject(&(&1.id == player.id))
            |> Enum.sort_by(&(-(&1.overall || 0)))
            |> Enum.take(5)
          else
            []
          end

        {:ok,
         %{
           player: player,
           club_team: club_team,
           club_matches: club_matches,
           teammates: teammates,
           top_skills: top_skills(player)
         }}
    end
  end

  @doc """
  Squad of a club from the FIFA dataset.

  Arguments: `club` (required), `limit`, `sort_by`.
  """
  @spec club_squad(Graph.t(), map) :: {:ok, map} | {:error, tuple}
  def club_squad(graph, args) do
    case Filters.get(args, :club) || Filters.get(args, :team) do
      nil ->
        {:error, {:missing_argument, :club}}

      club ->
        # only claim a club node when the query really names it, so a squad for
        # "Santos Laguna" is not labelled (and illustrated) with Santos of SP
        team =
          graph
          |> Graph.find_teams(club, 1)
          |> List.first()
          |> then(fn team -> if team && same_club?(club, team), do: team end)

        {:ok, result} = search(graph, %{club: club, limit: :all, sort_by: "overall"})

        cond do
          result.total > 0 ->
            {:ok, squad_result(graph, team, club, result.players)}

          team != nil ->
            {:error,
             {:club_not_in_player_data, team.name, clubs_with_players(graph) |> Enum.take(15)}}

          true ->
            {:error, {:club_not_found, club, clubs_with_players(graph) |> Enum.take(15)}}
        end
    end
  end

  defp squad_result(graph, team, club, players) do
    ratings = players |> Enum.map(& &1.overall) |> Enum.reject(&is_nil/1)
    ages = players |> Enum.map(& &1.age) |> Enum.reject(&is_nil/1)

    %{
      team: team,
      club_label: (team && team.name) || club,
      players: players,
      size: length(players),
      average_overall: average(ratings),
      average_age: average(ages),
      best_player: Enum.max_by(players, &(&1.overall || 0), fn -> nil end),
      nationalities:
        players
        |> Enum.frequencies_by(& &1.nationality)
        |> Enum.sort_by(fn {_, count} -> -count end),
      by_position:
        players
        |> Enum.group_by(&Player.position_group/1)
        |> Map.new(fn {group, list} -> {group, Enum.sort_by(list, &(-(&1.overall || 0)))} end),
      recent_matches: if(team, do: Enum.take(Graph.matches_for_team(graph, team.id), 5), else: [])
    }
  end

  @doc """
  Aggregated view of players of a nationality across clubs.

  Arguments: `nationality` (default "Brazil"), `brazilian_clubs_only`, `limit`.
  """
  @spec nationality_report(Graph.t(), map) :: {:ok, map} | {:error, tuple}
  def nationality_report(graph, args \\ %{}) do
    nationality = Filters.get(args, :nationality) || "Brazil"
    limit = Filters.limit(Filters.get(args, :limit), 10)

    {:ok, result} =
      search(graph, %{nationality: nationality, limit: :all, sort_by: "overall"})

    players = result.players

    by_club =
      players
      |> Enum.filter(& &1.club_id)
      |> Enum.group_by(& &1.club_id)
      |> Enum.map(fn {club_id, list} ->
        %{
          team: Graph.team(graph, club_id),
          count: length(list),
          average_overall: average(Enum.map(list, & &1.overall) |> Enum.reject(&is_nil/1)),
          best: Enum.max_by(list, &(&1.overall || 0), fn -> nil end)
        }
      end)
      |> Enum.sort_by(&{-&1.count, -(&1.average_overall || 0)})

    {:ok,
     %{
       nationality: nationality,
       total: length(players),
       top_players: Enum.take(players, limit),
       at_brazilian_clubs: Enum.sum(Enum.map(by_club, & &1.count)),
       by_brazilian_club: by_club,
       average_overall: average(Enum.map(players, & &1.overall) |> Enum.reject(&is_nil/1)),
       average_age: average(Enum.map(players, & &1.age) |> Enum.reject(&is_nil/1))
     }}
  end

  @doc "Brazilian clubs that actually have players in the FIFA dataset."
  @spec clubs_with_players(Graph.t()) :: [binary]
  def clubs_with_players(graph) do
    graph.players_by_club
    |> Enum.map(fn {club_id, ids} -> {Graph.team(graph, club_id), length(ids)} end)
    |> Enum.reject(fn {team, _} -> is_nil(team) end)
    |> Enum.sort_by(fn {_, count} -> -count end)
    |> Enum.map(fn {team, _} -> team.name end)
  end

  # --- helpers -------------------------------------------------------------

  defp matches_name?(_player, nil), do: true

  defp matches_name?(player, key) do
    player.name && String.contains?(normalise(player.name), key)
  end

  defp matches_nationality?(_player, nil), do: true

  defp matches_nationality?(player, key) do
    player.nationality && String.contains?(normalise(player.nationality), key)
  end

  # The team lookup is deliberately fuzzy, which is right for match queries but
  # too eager here: "Santos Laguna" (Mexico) resolves to Santos of São Paulo.
  # Only trust the graph link when the query really is that club's name.
  defp same_club?(query, team) do
    Names.similarity(Names.search_key(query), Names.search_key(team.name)) >= 0.9
  end

  defp matches_club?(_player, :any), do: true
  defp matches_club?(player, {:club_id, club_id}), do: player.club_id == club_id

  defp matches_club?(player, {:name, key}) do
    is_binary(player.club) and String.contains?(normalise(player.club), key)
  end

  defp best_name_match(graph, name) do
    key = normalise(name)

    graph.players
    |> Map.values()
    |> Enum.filter(&(&1.name && String.contains?(normalise(&1.name), key)))
    |> Enum.sort_by(&{String.length(&1.name), -(&1.overall || 0)})
    |> List.first()
  end

  defp name_suggestions(graph, name) do
    key = normalise(name)

    graph.players
    |> Map.values()
    |> Enum.sort_by(&(-String.jaro_distance(normalise(&1.name || ""), key)))
    |> Enum.take(5)
    |> Enum.map(& &1.name)
  end

  defp top_skills(%Player{skills: skills}) when map_size(skills) > 0 do
    skills
    |> Enum.sort_by(fn {_, value} -> -value end)
    |> Enum.take(6)
  end

  defp top_skills(_), do: []

  defp normalise(value) do
    value |> to_string() |> Names.ascii() |> String.downcase() |> String.trim()
  end

  defp position_group(nil), do: nil

  defp position_group(value) when is_binary(value) do
    case value |> String.downcase() |> String.trim() do
      "forward" -> :forward
      "forwards" -> :forward
      "attacker" -> :forward
      "striker" -> :forward
      "midfielder" -> :midfielder
      "midfielders" -> :midfielder
      "defender" -> :defender
      "defenders" -> :defender
      "goalkeeper" -> :goalkeeper
      "goalkeepers" -> :goalkeeper
      "gk" -> :goalkeeper
      _ -> nil
    end
  end

  defp position_group(value) when is_atom(value), do: value

  defp sort_key(nil), do: :overall

  defp sort_key(value) when is_binary(value) do
    case value |> String.downcase() |> String.trim() do
      "potential" -> :potential
      "age" -> :age
      "value" -> :value
      "name" -> :name
      _ -> :overall
    end
  end

  defp sort_key(value) when is_atom(value), do: value

  defp sort_value(player, :name), do: player.name || ""
  defp sort_value(player, :age), do: player.age || 999
  defp sort_value(player, :value), do: -(player.value_eur || 0)
  defp sort_value(player, :potential), do: -(player.potential || 0)
  defp sort_value(player, _), do: -(player.overall || 0)

  defp average([]), do: nil
  defp average(values), do: Float.round(Enum.sum(values) / length(values), 1)
end
