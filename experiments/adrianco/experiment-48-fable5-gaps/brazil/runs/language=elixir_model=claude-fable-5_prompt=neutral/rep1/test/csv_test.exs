defmodule BrazilianSoccerMcp.CSVTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccerMcp.CSV

  describe "Given a CSV binary, when parsed" do
    test "then simple rows split on commas and newlines" do
      assert CSV.parse("a,b,c\n1,2,3\n") == [["a", "b", "c"], ["1", "2", "3"]]
    end

    test "then quoted fields keep embedded commas, quotes, and newlines" do
      csv = ~s("Jul 1, 2004",plain,"say ""hi""","line1\nline2"\n)
      assert CSV.parse(csv) == [["Jul 1, 2004", "plain", "say \"hi\"", "line1\nline2"]]
    end

    test "then CRLF line endings and a UTF-8 BOM are handled" do
      csv = "﻿a,b\r\n1,2\r\n"
      assert CSV.parse(csv) == [["a", "b"], ["1", "2"]]
    end

    test "then UTF-8 accented text survives intact" do
      assert CSV.parse("team\nSão Paulo\nGrêmio\nAvaí\n") ==
               [["team"], ["São Paulo"], ["Grêmio"], ["Avaí"]]
    end

    test "then a file without a trailing newline still yields the last row" do
      assert CSV.parse("a,b\n1,2") == [["a", "b"], ["1", "2"]]
    end

    test "then empty fields are preserved" do
      assert CSV.parse("a,,c\n,,\n") == [["a", "", "c"], ["", "", ""]]
    end
  end

  describe "Given a header row, when converting rows to maps" do
    test "then each row becomes a map keyed by header" do
      assert CSV.rows_to_maps([["x", "y"], ["1", "2"]]) == [%{"x" => "1", "y" => "2"}]
    end
  end
end
