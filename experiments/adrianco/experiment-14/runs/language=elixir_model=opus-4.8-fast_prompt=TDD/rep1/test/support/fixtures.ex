defmodule BrazilianSoccer.Fixtures do
  @moduledoc "Small hand-built datasets for query tests."

  alias BrazilianSoccer.{Dataset, Match, Player}

  def match(attrs), do: Match.new(attrs)

  @doc """
  A compact dataset with a Fla x Flu rivalry, a couple of other teams, two
  seasons, and a handful of players.
  """
  def dataset do
    matches = [
      match(competition: "Brasileirão Série A", season: 2023, round: "22", date: "2023-09-03", home_team: "Flamengo", away_team: "Fluminense", home_goals: 2, away_goals: 1),
      match(competition: "Brasileirão Série A", season: 2023, round: "8", date: "2023-05-28", home_team: "Fluminense", away_team: "Flamengo", home_goals: 1, away_goals: 0),
      match(competition: "Brasileirão Série A", season: 2023, round: "10", date: "2023-06-15", home_team: "Flamengo", away_team: "Palmeiras", home_goals: 0, away_goals: 0),
      match(competition: "Brasileirão Série A", season: 2023, round: "12", date: "2023-07-01", home_team: "Palmeiras", away_team: "Flamengo", home_goals: 3, away_goals: 1),
      match(competition: "Brasileirão Série A", season: 2022, round: "1", date: "2022-04-10", home_team: "Flamengo", away_team: "Fluminense", home_goals: 1, away_goals: 1),
      match(competition: "Copa do Brasil", season: 2023, round: "Final", date: "2023-10-20", home_team: "Flamengo", away_team: "Palmeiras", home_goals: 2, away_goals: 0)
    ]

    players = [
      player(1, "Gabriel Barbosa", "Brazil", 84, "Flamengo", "ST"),
      player(2, "Pedro", "Brazil", 80, "Flamengo", "ST"),
      player(3, "Neymar Jr", "Brazil", 92, "Paris Saint-Germain", "LW"),
      player(4, "Lionel Messi", "Argentina", 93, "Paris Saint-Germain", "RW"),
      player(5, "Endrick", "Brazil", 70, "Palmeiras", "ST")
    ]

    Dataset.new(matches, players)
  end

  defp player(id, name, nat, overall, club, pos) do
    %Player{
      id: id,
      name: name,
      nationality: nat,
      overall: overall,
      club: club,
      club_key: BrazilianSoccer.TeamName.base(club),
      position: pos
    }
  end
end
