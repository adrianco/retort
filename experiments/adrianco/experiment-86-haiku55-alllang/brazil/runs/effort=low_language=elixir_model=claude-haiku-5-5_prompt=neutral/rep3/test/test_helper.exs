ExUnit.start()

defmodule BrazilianSoccerMcp.Fixtures do
  @moduledoc """
  Small hand-checked dataset used by the unit tests.

  2023 Brasileirão (four league matches, plus one Copa do Brasil match):

      Alpha 2-1 Beta    (Mar 1)    Beta 0-0 Gamma  (Mar 8)
      Gamma 3-1 Alpha   (Mar 15)   Alpha 0-0 Gamma (Apr 1)
      Alpha 4-0 Beta    (May 1, Copa do Brasil)

  2022 Brasileirão: Alpha 1-0 Gamma (Jun 1).

  Expected 2023 league table: Gamma 5 pts, Alpha 4 pts, Beta 1 pt.
  """

  alias BrazilianSoccerMcp.{Match, Player}

  def matches do
    [
      match(~D[2023-03-01], "brasileirao", 2023, "1", "Alpha", "Beta", 2, 1),
      match(~D[2023-03-08], "brasileirao", 2023, "1", "Beta", "Gamma", 0, 0),
      match(~D[2023-03-15], "brasileirao", 2023, "2", "Gamma", "Alpha", 3, 1),
      match(~D[2023-04-01], "brasileirao", 2023, "3", "Alpha", "Gamma", 0, 0),
      match(~D[2023-05-01], "copa_do_brasil", 2023, "1", "Alpha", "Beta", 4, 0),
      match(~D[2022-06-01], "brasileirao", 2022, "9", "Alpha", "Gamma", 1, 0)
    ]
  end

  def players do
    [
      player("Ana Silva", "Brazil", "Alpha", 85, "ST"),
      player("Bruno Costa", "Brazil", "Alpha", 80, "CM"),
      player("Carlos Ruiz", "Argentina", "Beta", 78, "GK"),
      player("Diego Lima", "Brazil", "Gamma", 70, "RB")
    ]
  end

  def data, do: %{matches: matches(), players: players()}

  def match(date, competition, season, round, home, away, home_goals, away_goals) do
    Match.new(%{
      date: date,
      competition: competition,
      season: season,
      round: round,
      home: home,
      away: away,
      home_goals: home_goals,
      away_goals: away_goals
    })
  end

  def player(name, nationality, club, overall, position) do
    Player.new(%{
      name: name,
      age: 25,
      nationality: nationality,
      overall: overall,
      potential: overall,
      club: club,
      position: position,
      value: nil
    })
  end
end
