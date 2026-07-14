defmodule BrSoccer.LoaderTest do
  use ExUnit.Case, async: true
  alias BrSoccer.Loader

  test "parses ISO dates with and without time" do
    assert Loader.parse_date("2012-05-19 18:30:00") == ~D[2012-05-19]
    assert Loader.parse_date("2023-09-24") == ~D[2023-09-24]
  end

  test "parses Brazilian DD/MM/YYYY dates" do
    assert Loader.parse_date("29/03/2003") == ~D[2003-03-29]
    assert Loader.parse_date("9/3/2003") == ~D[2003-03-09]
  end

  test "returns nil for blank or malformed dates" do
    assert Loader.parse_date("") == nil
    assert Loader.parse_date(nil) == nil
    assert Loader.parse_date("not a date") == nil
    assert Loader.parse_date("2003-13-40") == nil
  end

  test "to_int tolerates floats, whitespace and blanks" do
    assert Loader.to_int("3") == 3
    assert Loader.to_int("2.0") == 2
    assert Loader.to_int(" 5 ") == 5
    assert Loader.to_int("") == nil
    assert Loader.to_int("NA") == nil
  end
end
