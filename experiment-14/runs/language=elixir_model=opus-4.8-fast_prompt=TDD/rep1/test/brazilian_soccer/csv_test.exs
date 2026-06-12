defmodule BrazilianSoccer.CSVTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccer.CSV

  describe "parse/1" do
    test "parses simple rows" do
      assert CSV.parse("a,b,c\n1,2,3\n") == [["a", "b", "c"], ["1", "2", "3"]]
    end

    test "handles quoted fields" do
      assert CSV.parse(~s("a","b","c")) == [["a", "b", "c"]]
    end

    test "handles commas inside quoted fields" do
      assert CSV.parse(~s(x,"Jul 1, 2004",y)) == [["x", "Jul 1, 2004", "y"]]
    end

    test "handles escaped double quotes inside quoted fields" do
      assert CSV.parse(~s("she said ""hi""")) == [[~s(she said "hi")]]
    end

    test "handles newlines inside quoted fields" do
      assert CSV.parse(~s("line1\nline2",b)) == [["line1\nline2", "b"]]
    end

    test "handles \\r\\n line endings" do
      assert CSV.parse("a,b\r\n1,2\r\n") == [["a", "b"], ["1", "2"]]
    end

    test "ignores a trailing empty line" do
      assert CSV.parse("a,b\n") == [["a", "b"]]
    end

    test "preserves empty fields" do
      assert CSV.parse("a,,c") == [["a", "", "c"]]
    end

    test "strips a UTF-8 BOM at the start of the file" do
      assert CSV.parse("﻿a,b\n1,2") == [["a", "b"], ["1", "2"]]
    end
  end

  describe "parse_to_maps/1" do
    test "uses the first row as headers and maps remaining rows" do
      csv = "name,age\nAlice,30\nBob,25\n"

      assert CSV.parse_to_maps(csv) == [
               %{"name" => "Alice", "age" => "30"},
               %{"name" => "Bob", "age" => "25"}
             ]
    end
  end
end
