defmodule BrazilianSoccer.Dataset do
  @moduledoc """
  An in-memory collection of normalized matches and players. This is the value
  that the query modules operate on.
  """

  alias BrazilianSoccer.{Match, Player}

  @type t :: %__MODULE__{
          matches: [Match.t()],
          players: [Player.t()]
        }

  defstruct matches: [], players: []

  @doc "Build a dataset from lists of matches and players."
  @spec new([Match.t()], [Player.t()]) :: t()
  def new(matches \\ [], players \\ []) do
    %__MODULE__{matches: matches, players: players}
  end
end
