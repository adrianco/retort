defmodule BrazilianSoccerMcp.Player do
  @moduledoc """
  One player from the FIFA dataset.

  `name_key`, `club_key` and `nationality_key` are normalized forms used for
  matching. `club_key` uses the same `TeamName.key/1` as match data, which is
  what lets player and match queries join on a club.
  """

  alias BrazilianSoccerMcp.TeamName

  defstruct [
    :name,
    :age,
    :nationality,
    :overall,
    :potential,
    :club,
    :position,
    :value,
    :name_key,
    :club_key,
    :nationality_key
  ]

  @type t :: %__MODULE__{}

  @doc "Builds a player, computing the normalized lookup keys."
  @spec new(map()) :: t()
  def new(attrs) do
    attrs = Map.new(attrs)

    struct!(
      __MODULE__,
      Map.merge(attrs, %{
        name_key: TeamName.normalize(attrs.name),
        club_key: attrs.club && TeamName.key(attrs.club),
        nationality_key: attrs.nationality && TeamName.normalize(attrs.nationality)
      })
    )
  end
end
