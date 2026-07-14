defmodule BookApiTest do
  use ExUnit.Case
  doctest BookApi

  test "greets the world" do
    assert BookApi.hello() == :world
  end
end
