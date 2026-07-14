defmodule BrazilianSoccerTest do
  use ExUnit.Case

  test "main module defines entry point" do
    fns = BrazilianSoccer.__info__(:functions)
    assert {:main, 0} in fns or {:main, 1} in fns
  end
end
