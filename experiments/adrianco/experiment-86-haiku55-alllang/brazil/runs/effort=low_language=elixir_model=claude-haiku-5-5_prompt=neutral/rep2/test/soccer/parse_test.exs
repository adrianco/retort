defmodule SoccerMcp.ParseTest do
  # Feature: date and number parsing across the datasets' formats
  use ExUnit.Case, async: true

  alias SoccerMcp.Parse

  describe "Feature: date formats" do
    test "Scenario: ISO dates with and without a time" do
      # Given ISO dates
      # When I parse them
      # Then both give the same calendar date
      assert Parse.date("2023-09-24") == ~D[2023-09-24]
      assert Parse.date("2012-05-19 18:30:00") == ~D[2012-05-19]
    end

    test "Scenario: Brazilian DD/MM/YYYY dates" do
      # Given a Brazilian-format date
      # When I parse it
      # Then day and month are not swapped
      assert Parse.date("29/03/2003") == ~D[2003-03-29]
    end

    test "Scenario: unreadable dates give nil" do
      # Given text that is not a date
      # When I parse it
      # Then the result is nil
      assert Parse.date("not a date") == nil
      assert Parse.date("") == nil
      assert Parse.date("31/02/2003") == nil
      assert Parse.date(nil) == nil
    end
  end

  describe "Feature: numeric fields" do
    test "Scenario: float-formatted goals become integers" do
      # Given goals written as floats or integers
      # When I parse them
      # Then they are whole numbers
      assert Parse.int("1.0") == 1
      assert Parse.int("2") == 2
      assert Parse.int(" 3 ") == 3
    end

    test "Scenario: empty fields are nil, not zero" do
      # Given an unplayed match with no score
      # When I parse the score
      # Then the result is nil so the match can be skipped
      assert Parse.int("") == nil
      assert Parse.int(nil) == nil
    end
  end
end
