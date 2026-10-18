defmodule BrazilianSoccer.CSVTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccer.CSV

  describe "Scenario: parsing quoted and multi-line fields" do
    test "Given quoted commas and doubled quotes, then fields are kept verbatim" do
      rows = CSV.parse_rows(~s(a,"b, c","say ""hi""",d\n))
      assert rows == [["a", "b, c", ~s(say "hi"), "d"]]
    end

    test "Given a quoted field containing a newline, then it stays in one field" do
      assert CSV.parse_rows(~s("line1\nline2",x\n)) == [["line1\nline2", "x"]]
    end
  end

  describe "Scenario: line endings and byte-order mark" do
    test "Given CRLF line endings, then rows split correctly" do
      assert CSV.parse_rows("a,b\r\n1,2\r\n") == [["a", "b"], ["1", "2"]]
    end

    test "Given a UTF-8 BOM, then it is stripped from the first header" do
      [row] = CSV.parse_with_headers("\xEF\xBB\xBF,ID\n0,7\n")
      assert row == %{"" => "0", "ID" => "7"}
    end

    test "Given a file without a trailing newline, then the last row is kept" do
      assert CSV.parse_rows("a,b\n1,2") == [["a", "b"], ["1", "2"]]
    end
  end

  describe "Scenario: header-keyed rows" do
    test "Given blank lines and short rows, then blanks are skipped and short rows padded" do
      content = "x,y,z\n1,2,3\n\n4\n"

      assert CSV.parse_with_headers(content) == [
               %{"x" => "1", "y" => "2", "z" => "3"},
               %{"x" => "4", "y" => "", "z" => ""}
             ]
    end

    test "Given an empty file, then no rows are returned" do
      assert CSV.parse_with_headers("") == []
    end

    test "Given UTF-8 text, then accented characters survive intact" do
      [row] = CSV.parse_with_headers("name\nSão Paulo\n")
      assert row["name"] == "São Paulo"
    end
  end
end
