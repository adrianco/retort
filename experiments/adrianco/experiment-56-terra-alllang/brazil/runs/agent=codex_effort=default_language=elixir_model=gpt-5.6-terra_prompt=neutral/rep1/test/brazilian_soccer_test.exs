defmodule BrazilianSoccerTest do
  use ExUnit.Case, async: true
  alias BrazilianSoccer.Data

  setup do
    data = %{
      matches: [
        %{
          home: "Flamengo-RJ",
          away: "Fluminense-RJ",
          home_key: "flamengo",
          away_key: "fluminense",
          home_goals: 2,
          away_goals: 1,
          date: ~D[2023-09-03],
          season: 2023,
          competition: "Brasileirão",
          stage: "22"
        },
        %{
          home: "Fluminense",
          away: "Flamengo",
          home_key: "fluminense",
          away_key: "flamengo",
          home_goals: 0,
          away_goals: 0,
          date: ~D[2023-05-28],
          season: 2023,
          competition: "Brasileirão",
          stage: "8"
        },
        %{
          home: "Palmeiras",
          away: "Santos",
          home_key: "palmeiras",
          away_key: "santos",
          home_goals: 3,
          away_goals: 0,
          date: ~D[2023-06-01],
          season: 2023,
          competition: "Brasileirão",
          stage: "9"
        }
      ],
      players: [
        %{
          name: "Gabriel Barbosa",
          nationality: "Brazil",
          club: "Flamengo",
          position: "ST",
          overall: 82,
          age: 26,
          id: "1",
          potential: 83,
          jersey_number: 9
        }
      ]
    }

    %{data: data}
  end

  test "normalizes suffixes and finds head-to-head matches", %{data: data} do
    matches = BrazilianSoccer.search_matches(data, team: "Flamengo", opponent: "Fluminense")
    assert length(matches) == 2
    assert BrazilianSoccer.head_to_head(data, "Flamengo", "Fluminense").first_wins == 1
  end

  test "calculates team statistics and standings", %{data: data} do
    stats = BrazilianSoccer.team_statistics(data, "Flamengo-RJ", season: 2023)
    assert %{matches: 2, wins: 1, draws: 1, losses: 0, goals_for: 2, goals_against: 1} = stats

    assert [%{team: "Flamengo", points: 4, position: 1} | _] =
             BrazilianSoccer.standings(data, 2023)
  end

  test "searches players case and accent insensitively", %{data: data} do
    assert [%{name: "Gabriel Barbosa"}] =
             BrazilianSoccer.search_players(data, name: "gabriel", club: "flamengo")
  end

  test "handles both supported date formats" do
    assert ~D[2003-03-29] = BrazilianSoccer.Normalize.date!("29/03/2003")
    assert ~D[2012-05-19] = BrazilianSoccer.Normalize.date!("2012-05-19 18:30:00")
  end

  test "loads all provided CSV datasets" do
    data = Data.load("data/kaggle")
    assert length(data.matches) > 20_000
    assert length(data.players) > 18_000
  end
end
