defmodule SoccerMcp.DoctestTest do
  # Runs the worked examples embedded in the module docs.
  use ExUnit.Case, async: true

  doctest SoccerMcp.Team
  doctest SoccerMcp.Parse
  doctest SoccerMcp.Match
end
