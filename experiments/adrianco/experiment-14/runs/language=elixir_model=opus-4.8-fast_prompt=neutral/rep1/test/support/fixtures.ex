defmodule BrSoccer.Fixtures do
  @moduledoc "Small, deterministic dataset used by unit tests."

  alias BrSoccer.{Match, Player, TeamName}

  @doc "Build a match struct from raw team names (keys are derived automatically)."
  def match(competition, season, home, away, hg, ag, opts \\ []) do
    %Match{
      competition: competition,
      source: Keyword.get(opts, :source, :brasileirao_csv),
      season: season,
      date: Keyword.get(opts, :date),
      round: Keyword.get(opts, :round),
      stage: Keyword.get(opts, :stage),
      home: TeamName.display(home),
      away: TeamName.display(away),
      home_key: TeamName.key(home),
      away_key: TeamName.key(away),
      home_goal: hg,
      away_goal: ag
    }
  end

  @doc "A three-team round-robin Brasileirão 2020 plus a couple of other competitions."
  def matches do
    [
      # Brasileirão 2020 — Alpha, Beta, Gamma (single round-robin home & away)
      match(:brasileirao, 2020, "Alpha", "Beta", 2, 0, date: ~D[2020-08-01], round: 1),
      match(:brasileirao, 2020, "Beta", "Alpha", 1, 1, date: ~D[2020-08-08], round: 2),
      match(:brasileirao, 2020, "Alpha", "Gamma", 3, 1, date: ~D[2020-08-15], round: 3),
      match(:brasileirao, 2020, "Gamma", "Alpha", 0, 0, date: ~D[2020-08-22], round: 4),
      match(:brasileirao, 2020, "Beta", "Gamma", 2, 2, date: ~D[2020-08-29], round: 5),
      match(:brasileirao, 2020, "Gamma", "Beta", 1, 0, date: ~D[2020-09-05], round: 6),
      # Another season for the same clubs (Alpha vs Beta)
      match(:brasileirao, 2019, "Alpha", "Beta", 4, 2, date: ~D[2019-05-10], round: 1),
      # A cup tie and a Libertadores tie
      match(:copa_do_brasil, 2020, "Alpha", "Gamma", 1, 0, date: ~D[2020-06-01], stage: "final"),
      match(:libertadores, 2020, "Alpha", "Beta", 5, 0, date: ~D[2020-03-01], stage: "group stage")
    ]
  end

  @doc "A handful of FIFA-style players. Some clubs match Brazilian team keys."
  def players do
    [
      player(1, "Neymar Jr", "Brazil", 92, "Paris Saint-Germain", "LW", 27),
      player(2, "Alpha Star", "Brazil", 80, "Alpha", "ST", 24),
      player(3, "Beta Keeper", "Brazil", 75, "Beta", "GK", 30),
      player(4, "Foreign Guy", "Argentina", 85, "Alpha", "CB", 28),
      player(5, "Old Timer", "Brazil", 70, "Alpha", "CM", 35)
    ]
  end

  def data, do: %{matches: matches(), players: players()}

  defp player(id, name, nat, overall, club, pos, age) do
    %Player{
      id: id,
      name: name,
      nationality: nat,
      overall: overall,
      potential: overall + 2,
      club: club,
      club_key: TeamName.key(club),
      position: pos,
      age: age
    }
  end
end
