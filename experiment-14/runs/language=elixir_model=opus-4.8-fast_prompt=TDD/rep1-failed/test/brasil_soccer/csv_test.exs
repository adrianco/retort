defmodule BrasilSoccer.CSVTest do
  use ExUnit.Case, async: true

  alias BrasilSoccer.CSV

  describe "parse/1" do
    test "parses a simple header + rows into a list of maps" do
      content = "a,b,c\n1,2,3\n4,5,6\n"

      assert CSV.parse(content) == [
               %{"a" => "1", "b" => "2", "c" => "3"},
               %{"a" => "4", "b" => "5", "c" => "6"}
             ]
    end

    test "handles quoted fields containing commas" do
      content = ~s(name,note\n"Doe, John","hello, world"\n)

      assert CSV.parse(content) == [
               %{"name" => "Doe, John", "note" => "hello, world"}
             ]
    end

    test "handles escaped double quotes inside quoted fields" do
      content = ~s(quote\n"She said ""hi""")

      assert CSV.parse(content) == [%{"quote" => ~s(She said "hi")}]
    end

    test "strips a UTF-8 BOM from the header" do
      content = "﻿a,b\n1,2\n"
      assert CSV.parse(content) == [%{"a" => "1", "b" => "2"}]
    end

    test "preserves accented UTF-8 characters" do
      content = "team\nGrêmio\nAvaí\n"
      assert CSV.parse(content) == [%{"team" => "Grêmio"}, %{"team" => "Avaí"}]
    end

    test "handles CRLF line endings and ignores trailing blank lines" do
      content = "a,b\r\n1,2\r\n\r\n"
      assert CSV.parse(content) == [%{"a" => "1", "b" => "2"}]
    end

    test "pads missing trailing columns with empty strings" do
      content = "a,b,c\n1,2\n"
      assert CSV.parse(content) == [%{"a" => "1", "b" => "2", "c" => ""}]
    end
  end

  describe "parse_file/1" do
    @tag :tmp_dir
    test "reads and parses a file from disk", %{tmp_dir: dir} do
      path = Path.join(dir, "x.csv")
      File.write!(path, "a,b\n1,2\n")
      assert CSV.parse_file(path) == [%{"a" => "1", "b" => "2"}]
    end
  end
end
