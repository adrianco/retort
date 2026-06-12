defmodule BrazilianSoccer.Queries.Players do
  alias BrazilianSoccer.DataStore

  def search_by_name(name) do
    term = String.downcase(name)
    DataStore.players() |> Enum.filter(fn p ->
      String.contains?(String.downcase(p.name), term)
    end)
  end

  def search_by_nationality(nationality) do
    term = String.downcase(nationality)
    DataStore.players() |> Enum.filter(fn p ->
      String.contains?(String.downcase(p.nationality), term)
    end)
  end

  def search_by_club(club) do
    term = String.downcase(club)
    DataStore.players() |> Enum.filter(fn p ->
      String.contains?(String.downcase(p.club), term)
    end)
  end

  def search_by_position(position) do
    pos = String.upcase(String.trim(position))
    DataStore.players() |> Enum.filter(fn p -> p.position == pos end)
  end

  def top_rated(limit, opts \\ []) do
    players = DataStore.players()

    players =
      case Keyword.get(opts, :nationality) do
        nil -> players
        nat ->
          term = String.downcase(nat)
          Enum.filter(players, fn p -> String.contains?(String.downcase(p.nationality), term) end)
      end

    players =
      case Keyword.get(opts, :club) do
        nil -> players
        club ->
          term = String.downcase(club)
          Enum.filter(players, fn p -> String.contains?(String.downcase(p.club), term) end)
      end

    players
    |> Enum.filter(fn p -> is_integer(p.overall) end)
    |> Enum.sort_by(fn p -> -p.overall end)
    |> Enum.take(limit)
  end

  def players_by_club_with_nationality(club, nationality) do
    club_term = String.downcase(club)
    nat_term = String.downcase(nationality)

    DataStore.players()
    |> Enum.filter(fn p ->
      String.contains?(String.downcase(p.club), club_term) and
        String.contains?(String.downcase(p.nationality), nat_term)
    end)
  end
end
