defmodule BrasilSoccer.Fixtures do
  @moduledoc "Small hand-built datasets for unit testing the query layer."

  alias BrasilSoccer.Match

  @doc "A handful of matches spanning competitions, seasons, and results."
  def matches do
    [
      m("Brasileirão", 2023, "1", "2023-04-16", "Flamengo-RJ", "Fluminense-RJ", 2, 1),
      m("Brasileirão", 2023, "8", "2023-05-28", "Fluminense-RJ", "Flamengo-RJ", 1, 0),
      m("Brasileirão", 2023, "22", "2023-09-03", "Flamengo-RJ", "Fluminense-RJ", 2, 0),
      m("Brasileirão", 2023, "5", "2023-05-01", "Palmeiras-SP", "Santos-SP", 4, 0),
      m("Brasileirão", 2023, "9", "2023-06-01", "Santos-SP", "Palmeiras-SP", 1, 1),
      m("Brasileirão", 2022, "3", "2022-05-10", "Flamengo-RJ", "Palmeiras-SP", 0, 3),
      m("Copa do Brasil", 2023, "Final", "2023-09-24", "São Paulo-SP", "Flamengo-RJ", 1, 1)
    ]
  end

  @doc "A small Brasileirão season that produces a determinate table."
  def mini_season do
    [
      m("Brasileirão", 2019, "1", "2019-04-28", "Flamengo", "Santos", 2, 0),
      m("Brasileirão", 2019, "2", "2019-05-05", "Santos", "Palmeiras", 1, 1),
      m("Brasileirão", 2019, "3", "2019-05-12", "Palmeiras", "Flamengo", 0, 1),
      m("Brasileirão", 2019, "4", "2019-05-19", "Flamengo", "Palmeiras", 3, 0),
      m("Brasileirão", 2019, "5", "2019-05-26", "Santos", "Flamengo", 0, 2),
      m("Brasileirão", 2019, "6", "2019-06-02", "Palmeiras", "Santos", 2, 1)
    ]
  end

  def players do
    [
      p("Neymar Jr", "Brazil", 92, "LW", "Paris Saint-Germain"),
      p("Gabriel Barbosa", "Brazil", 81, "ST", "Flamengo"),
      p("Bruno Henrique", "Brazil", 79, "LW", "Flamengo"),
      p("Dudu", "Brazil", 80, "RM", "Palmeiras"),
      p("L. Messi", "Argentina", 94, "RW", "FC Barcelona"),
      p("Soteldo", "Venezuela", 75, "LW", "Santos")
    ]
  end

  defp m(comp, season, round, date, home, away, hg, ag) do
    Match.new(%{
      competition: comp,
      season: season,
      round: round,
      date: Date.from_iso8601!(date),
      home_team: home,
      away_team: away,
      home_goal: hg,
      away_goal: ag
    })
  end

  defp p(name, nat, overall, pos, club) do
    %{
      name: name,
      nationality: nat,
      overall: overall,
      potential: overall,
      position: pos,
      club: club,
      age: 27,
      jersey_number: 10,
      id: :erlang.phash2(name)
    }
  end
end
