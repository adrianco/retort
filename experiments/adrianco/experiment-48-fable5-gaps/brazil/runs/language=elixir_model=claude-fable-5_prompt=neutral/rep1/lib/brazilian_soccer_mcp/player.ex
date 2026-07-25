defmodule BrazilianSoccerMcp.Player do
  @moduledoc """
  A player record from the FIFA dataset. `:name_search` and `:club_search`
  hold accent-stripped lowercase forms used for matching.
  """

  defstruct [
    :id,
    :name,
    :name_search,
    :age,
    :nationality,
    :overall,
    :potential,
    :club,
    :club_search,
    :position,
    :jersey_number,
    :height,
    :weight,
    :value,
    :wage,
    :preferred_foot,
    skills: %{}
  ]

  @forwards ~w(ST CF LW RW LS RS LF RF)
  @midfielders ~w(CM CDM CAM LM RM LCM RCM LDM RDM LAM RAM)
  @defenders ~w(CB LB RB LCB RCB LWB RWB)

  @doc """
  Expand a position query ("forward", "midfielder", "defender", "goalkeeper",
  or an exact code like "GK"/"ST") into the list of position codes it covers.
  """
  def position_codes(query) do
    case query |> to_string() |> String.downcase() |> String.trim() do
      q when q in ["forward", "forwards", "attacker", "striker", "atacante"] -> @forwards
      q when q in ["midfielder", "midfielders", "midfield", "meia"] -> @midfielders
      q when q in ["defender", "defenders", "defence", "defense", "zagueiro"] -> @defenders
      q when q in ["goalkeeper", "goalkeepers", "keeper", "gk", "goleiro"] -> ["GK"]
      q -> [String.upcase(q)]
    end
  end
end
