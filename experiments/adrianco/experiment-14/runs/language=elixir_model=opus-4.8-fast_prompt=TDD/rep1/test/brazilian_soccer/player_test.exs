defmodule BrazilianSoccer.PlayerTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccer.Player

  @row %{
    "ID" => "158023",
    "Name" => "Neymar Jr",
    "Age" => "26",
    "Nationality" => "Brazil",
    "Overall" => "92",
    "Potential" => "93",
    "Club" => "Paris Saint-Germain",
    "Position" => "LW",
    "Jersey Number" => "10",
    "Height" => "5'9",
    "Weight" => "150lbs"
  }

  describe "from_row/1" do
    test "maps FIFA CSV columns into a struct with typed fields" do
      p = Player.from_row(@row)

      assert p.id == 158_023
      assert p.name == "Neymar Jr"
      assert p.age == 26
      assert p.nationality == "Brazil"
      assert p.overall == 92
      assert p.potential == 93
      assert p.club == "Paris Saint-Germain"
      assert p.position == "LW"
    end

    test "stores a normalized club key for matching" do
      p = Player.from_row(%{@row | "Club" => "São Paulo"})
      assert p.club_key == "sao paulo"
    end

    test "tolerates blank numeric fields" do
      p = Player.from_row(%{@row | "Overall" => "", "Age" => ""})
      assert p.overall == nil
      assert p.age == nil
    end
  end

  describe "brazilian?/1" do
    test "is true for Brazil nationality regardless of accent/case" do
      assert Player.brazilian?(Player.from_row(@row))
      assert Player.brazilian?(Player.from_row(%{@row | "Nationality" => "brazil"}))
    end

    test "is false for other nationalities" do
      refute Player.brazilian?(Player.from_row(%{@row | "Nationality" => "Argentina"}))
    end
  end
end
