defmodule BrSoccer.CSVTest do
  use ExUnit.Case, async: true
  alias BrSoccer.CSV

  test "parses simple rows into header-keyed maps" do
    csv = "a,b,c\n1,2,3\n4,5,6\n"
    assert CSV.parse_string(csv) == [
             %{"a" => "1", "b" => "2", "c" => "3"},
             %{"a" => "4", "b" => "5", "c" => "6"}
           ]
  end

  test "handles quoted fields with embedded commas and quotes" do
    csv = ~s(name,note\n"Boavista, RJ","said ""hi"""\n)
    assert [%{"name" => "Boavista, RJ", "note" => ~s(said "hi")}] = CSV.parse_string(csv)
  end

  test "strips a UTF-8 BOM from the first header cell" do
    csv = <<0xEF, 0xBB, 0xBF>> <> "id,name\n1,Messi\n"
    assert [%{"id" => "1", "name" => "Messi"}] = CSV.parse_string(csv)
  end

  test "preserves UTF-8 accented content" do
    csv = "team\nSão Paulo\nGrêmio\n"
    assert [%{"team" => "São Paulo"}, %{"team" => "Grêmio"}] = CSV.parse_string(csv)
  end

  test "handles CRLF line endings and ragged short rows" do
    csv = "a,b,c\r\n1,2\r\n"
    assert [%{"a" => "1", "b" => "2", "c" => ""}] = CSV.parse_string(csv)
  end

  test "supports newlines inside quoted fields" do
    csv = ~s(a,b\n"line1\nline2",x\n)
    assert [%{"a" => "line1\nline2", "b" => "x"}] = CSV.parse_string(csv)
  end
end
