defmodule BrSoccer.TeamNameTest do
  use ExUnit.Case, async: true
  alias BrSoccer.TeamName

  test "collapses state suffixes onto the bare club" do
    assert TeamName.same?("Flamengo-RJ", "Flamengo")
    assert TeamName.same?("Palmeiras-SP", "Palmeiras")
    assert TeamName.same?("Botafogo RJ", "Botafogo-RJ")
  end

  test "is accent-insensitive" do
    assert TeamName.same?("São Paulo", "Sao Paulo")
    assert TeamName.same?("Grêmio", "Gremio")
    assert TeamName.same?("Avaí", "Avai")
  end

  test "unifies descriptive names with short forms" do
    assert TeamName.same?("Atletico Mineiro", "Atletico-MG")
    assert TeamName.same?("Athletico Paranaense", "Athletico-PR")
    assert TeamName.same?("América FC (Minas Gerais)", "America-MG")
  end

  test "keeps genuinely distinct same-named clubs apart" do
    refute TeamName.same?("Atletico-MG", "Atletico-PR")
    refute TeamName.same?("Atletico-MG", "Atletico-GO")
    refute TeamName.same?("America-MG", "America-RN")
  end

  test "does not strip a club whose name ends in a state-like pair without a separator" do
    # "Flamengo" ends in "go" but there is no separator, so GO must not be stripped.
    assert TeamName.key("Flamengo") == "flamengo"
  end

  test "produces friendly display names" do
    assert TeamName.display("Flamengo-RJ") == "Flamengo"
    assert TeamName.display("Sao Paulo") == "São Paulo"
    assert TeamName.display("Gremio") == "Grêmio"
  end

  test "handles country-coded opponents from Libertadores" do
    assert TeamName.key("Nacional (URU)") == TeamName.key("Nacional")
  end
end
