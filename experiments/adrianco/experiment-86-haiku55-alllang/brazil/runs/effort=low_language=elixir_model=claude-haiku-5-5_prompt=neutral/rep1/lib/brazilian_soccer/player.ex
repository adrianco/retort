defmodule BrazilianSoccer.Player do
  @moduledoc "A player record from the FIFA player database."

  defstruct [
    :id,
    :name,
    :age,
    :nationality,
    :club,
    :position,
    :overall,
    :potential,
    :jersey_number,
    :value,
    :wage
  ]

  @type t :: %__MODULE__{
          id: integer() | nil,
          name: binary(),
          age: integer() | nil,
          nationality: binary(),
          club: binary(),
          position: binary(),
          overall: integer(),
          potential: integer() | nil,
          jersey_number: integer() | nil,
          value: binary(),
          wage: binary()
        }
end
