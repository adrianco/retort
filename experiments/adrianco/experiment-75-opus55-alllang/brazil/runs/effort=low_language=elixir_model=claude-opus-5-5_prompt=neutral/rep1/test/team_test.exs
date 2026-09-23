defmodule BrSoccer.TeamTest do
  use ExUnit.Case, async: true
  alias BrSoccer.{CSV, Data, Team}

  test "normalizes team name variations to one key" do
    for n <- ["Palmeiras-SP", "Palmeiras", "Palmeiras - SP", "SE Palmeiras"], do: assert(Team.canonical(n) == "palmeiras")
    for n <- ["São Paulo", "Sao Paulo", "São Paulo - SP", "Sao Paulo-SP"], do: assert(Team.canonical(n) == "sao paulo")
    assert Team.canonical("Sport Club Corinthians Paulista") == "corinthians"
    assert Team.canonical("Grêmio") == Team.canonical("Gremio RS")
    assert Team.canonical("Vasco Da Gama RJ") == "vasco"
    assert Team.canonical("EC Juventude") == Team.canonical("Juventude-RS")
  end

  test "keeps ambiguous clubs apart by state" do
    assert Team.canonical("Atlético Mineiro") == "atletico mg"
    assert Team.canonical("Atletico-MG") == "atletico mg"
    assert Team.canonical("Athletico-PR") == "atletico pr"
    assert Team.canonical("Atletico Paranaense") == "atletico pr"
    refute Team.matches?("flamengo do piaui", "Flamengo")
    assert Team.matches?("atletico mg", "Atletico")
  end

  test "parses multiple date formats" do
    assert Data.parse_date("2023-09-24") == ~D[2023-09-24]
    assert Data.parse_date("2012-05-19 18:30:00") == ~D[2012-05-19]
    assert Data.parse_date("29/03/2003") == ~D[2003-03-29]
  end

  test "CSV parser handles quotes, embedded commas and escaped quotes" do
    assert CSV.parse(~s(a,"b,c","d ""x"""\n1,2,3\n)) == [["a", "b,c", ~s(d "x")], ["1", "2", "3"]]
  end
end
