defmodule BrSoccer.Player do
  @moduledoc "A normalised FIFA player record."

  defstruct [
    :id,
    :name,
    :age,
    :nationality,
    :overall,
    :potential,
    :club,
    :club_key,
    :position,
    :jersey,
    :height,
    :weight,
    :value,
    :wage,
    :preferred_foot
  ]

  @type t :: %__MODULE__{}
end
