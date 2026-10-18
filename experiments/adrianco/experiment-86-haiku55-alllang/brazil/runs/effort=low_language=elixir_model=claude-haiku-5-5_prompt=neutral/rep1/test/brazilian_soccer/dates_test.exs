defmodule BrazilianSoccer.DatesTest do
  use ExUnit.Case, async: true

  doctest BrazilianSoccer.Dates

  alias BrazilianSoccer.Dates

  describe "Scenario: date formats in the datasets" do
    test "Given ISO dates with and without a time, then both parse" do
      assert Dates.parse("2023-09-24") == {:ok, ~D[2023-09-24]}
      assert Dates.parse("2012-05-19 18:30:00") == {:ok, ~D[2012-05-19]}
    end

    test "Given Brazilian DD/MM/YYYY dates, then day and month are not swapped" do
      assert Dates.parse("10/04/2022") == {:ok, ~D[2022-04-10]}
    end

    test "Given an impossible date, then parsing fails" do
      assert Dates.parse("31/02/2020") == :error
    end
  end
end
