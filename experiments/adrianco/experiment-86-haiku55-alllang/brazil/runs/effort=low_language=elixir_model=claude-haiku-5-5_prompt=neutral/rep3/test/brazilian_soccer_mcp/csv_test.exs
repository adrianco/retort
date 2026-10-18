defmodule BrazilianSoccerMcp.CSVTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccerMcp.CSV

  describe "Given a plain CSV" do
    test "When parsed Then each line becomes a row of fields" do
      assert CSV.parse("a,b,c\n1,2,3\n") == [["a", "b", "c"], ["1", "2", "3"]]
    end

    test "When it has CRLF line endings Then they are handled like LF" do
      assert CSV.parse("a,b\r\n1,2\r\n") == [["a", "b"], ["1", "2"]]
    end

    test "When it has no trailing newline Then the last row is kept" do
      assert CSV.parse("a,b\n1,2") == [["a", "b"], ["1", "2"]]
    end

    test "When it has blank lines Then they are skipped" do
      assert CSV.parse("a,b\n\n1,2\n\n") == [["a", "b"], ["1", "2"]]
    end
  end

  describe "Given quoted fields" do
    test "When a field contains a comma Then it stays one field" do
      assert CSV.parse(~s(name,club\n"Silva, Ana",Flamengo\n)) == [
               ["name", "club"],
               ["Silva, Ana", "Flamengo"]
             ]
    end

    test "When a field contains doubled quotes Then they unescape to one quote" do
      assert CSV.parse(~s("say ""hi""",x\n)) == [[~s(say "hi"), "x"]]
    end

    test "When a field contains a newline Then it is kept inside the field" do
      assert CSV.parse(~s("line one\nline two",x\n)) == [["line one\nline two", "x"]]
    end
  end

  describe "Given a file with a byte order mark and UTF-8 text" do
    test "When parsed Then the BOM is dropped and accents are preserved" do
      assert CSV.parse("﻿name,team\nAna,São Paulo\n") == [["name", "team"], ["Ana", "São Paulo"]]
    end
  end

  describe "Given a header row" do
    test "When parsed as maps Then each row is keyed by its header" do
      assert CSV.parse_maps("home,away\nFlamengo,Fluminense\n") == [
               %{"home" => "Flamengo", "away" => "Fluminense"}
             ]
    end

    test "When there are no rows Then the result is empty" do
      assert CSV.parse_maps("") == []
    end
  end
end
