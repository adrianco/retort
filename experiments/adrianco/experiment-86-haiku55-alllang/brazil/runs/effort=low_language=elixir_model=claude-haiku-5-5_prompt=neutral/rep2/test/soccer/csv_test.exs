defmodule SoccerMcp.CSVTest do
  # Feature: CSV reading
  #   The datasets use quoted fields, a BOM on one file and CRLF on some rows.
  use ExUnit.Case, async: true

  alias SoccerMcp.CSV

  describe "Feature: CSV parsing" do
    test "Scenario: quoted fields keep commas, quotes and newlines" do
      # Given a CSV with a quoted comma, a doubled quote and an embedded newline
      input = ~s(name,note\n"Smith, J","said ""hi""\nthere"\n)

      # When I parse it
      rows = CSV.parse(input)

      # Then each field keeps its literal content
      assert rows == [%{"name" => "Smith, J", "note" => ~s(said "hi"\nthere)}]
    end

    test "Scenario: a leading byte order mark is ignored" do
      # Given a file that starts with a UTF-8 BOM
      input = <<0xEF, 0xBB, 0xBF>> <> "ID,Name\n1,Gabriel\n"

      # When I parse it
      # Then the first header is "ID", not "﻿ID"
      assert [%{"ID" => "1", "Name" => "Gabriel"}] = CSV.parse(input)
    end

    test "Scenario: CRLF line endings and accented UTF-8 text" do
      # Given Windows line endings and accented team names
      input = "home,away\r\nGrêmio,São Paulo\r\nAvaí,Goiás\r\n"

      # When I parse it
      # Then the text is intact and no row carries a stray \r
      assert CSV.parse(input) == [
               %{"home" => "Grêmio", "away" => "São Paulo"},
               %{"home" => "Avaí", "away" => "Goiás"}
             ]
    end

    test "Scenario: empty input yields no rows" do
      # Given an empty file
      # When I parse it
      # Then there are no rows
      assert CSV.parse("") == []
    end
  end
end
