defmodule BookAPITest do
  use ExUnit.Case
  doctest BookAPI

  test "greets the world" do
    assert BookAPI.hello() == :world
  end
end
