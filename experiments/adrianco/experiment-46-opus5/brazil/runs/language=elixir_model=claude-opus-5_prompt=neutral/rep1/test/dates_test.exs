defmodule BrazilianSoccer.DatesTest do
  @moduledoc """
  Feature: Date parsing

  The datasets mix ISO dates, ISO timestamps, Brazilian `DD/MM/YYYY` dates and
  placeholders such as `NA`.
  """

  use ExUnit.Case, async: true

  alias BrazilianSoccer.Dates

  describe "Scenario: the formats found in the data" do
    test "Given an ISO date Then it parses with no time" do
      assert Dates.parse("2023-09-24") == {~D[2023-09-24], nil}
    end

    test "Given an ISO timestamp Then date and time are split" do
      assert Dates.parse("2012-05-19 18:30:00") == {~D[2012-05-19], ~T[18:30:00]}
    end

    test "Given a Brazilian date Then day and month are read in the right order" do
      assert Dates.parse("29/03/2003") == {~D[2003-03-29], nil}
      assert Dates.parse("06/04/2003") == {~D[2003-04-06], nil}
    end

    test "Given a quoted value Then quotes are stripped" do
      assert Dates.parse("\"2019-11-23\"") == {~D[2019-11-23], nil}
    end
  end

  describe "Scenario: missing and malformed values" do
    test "Given a placeholder Then nothing is parsed and nothing raises" do
      for value <- [nil, "", "NA", "-", "not a date", "99/99/9999"] do
        assert {nil, _} = Dates.parse(value), "failed for #{inspect(value)}"
      end
    end

    test "Given an impossible date Then it is rejected" do
      assert Dates.parse("2019-02-31") == {nil, nil}
    end
  end

  describe "Scenario: formatting" do
    test "Given a date Then it renders ISO, and a missing date says so" do
      assert Dates.format(~D[2019-11-23]) == "2019-11-23"
      assert Dates.format(nil) == "date unknown"
    end

    test "Given a date or a string When coercing Then a Date comes back" do
      assert Dates.to_date(~D[2019-11-23]) == ~D[2019-11-23]
      assert Dates.to_date("23/11/2019") == ~D[2019-11-23]
      assert Dates.to_date("nonsense") == nil
    end
  end
end
