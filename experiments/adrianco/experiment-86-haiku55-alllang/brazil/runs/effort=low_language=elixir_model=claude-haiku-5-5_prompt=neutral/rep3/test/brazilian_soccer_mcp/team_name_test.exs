defmodule BrazilianSoccerMcp.TeamNameTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccerMcp.TeamName

  describe "Given the same club written with different state suffixes" do
    test "When keyed Then the suffix is ignored" do
      keys = Enum.map(["Palmeiras-SP", "Palmeiras - SP", "Palmeiras"], &TeamName.key/1)
      assert keys == ["palmeiras", "palmeiras", "palmeiras"]
    end
  end

  describe "Given a parenthetical note" do
    test "When keyed Then the note is ignored" do
      assert TeamName.key("Nacional (URU)") == "nacional"
    end
  end

  describe "Given accented and unaccented spellings" do
    test "When keyed Then they produce the same key" do
      assert TeamName.key("São Paulo") == TeamName.key("Sao Paulo")
      assert TeamName.key("Grêmio") == TeamName.key("Gremio")
      assert TeamName.key("Avaí") == "avai"
    end
  end

  describe "Given a full official club name" do
    test "When keyed Then it maps to the short canonical key" do
      assert TeamName.key("Sport Club Corinthians Paulista") == "corinthians"
      assert TeamName.key("Sociedade Esportiva Palmeiras") == "palmeiras"
      assert TeamName.key("CR Flamengo") == "flamengo"
    end
  end

  describe "Given a team that should stay separate from a same-named club" do
    test "When keyed Then a different state keeps a different key" do
      refute TeamName.key("Botafogo SP") == TeamName.key("Botafogo RJ")
    end
  end

  describe "Given a raw name for display" do
    test "When displayed Then the state suffix and notes are removed" do
      assert TeamName.display("Palmeiras-SP") == "Palmeiras"
      assert TeamName.display("Nacional (URU)") == "Nacional"
      assert TeamName.display("São Paulo") == "São Paulo"
    end
  end
end
