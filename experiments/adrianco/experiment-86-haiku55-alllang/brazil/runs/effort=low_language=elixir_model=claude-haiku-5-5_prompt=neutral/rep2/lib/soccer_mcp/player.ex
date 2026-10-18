defmodule SoccerMcp.Player do
  @moduledoc """
  A player record from the FIFA player database (`fifa_data.csv`).

  Ratings are FIFA's 0-99 scale. `club` and `nationality` are kept as
  published; `SoccerMcp.Query.players/2` does the case- and accent-insensitive
  matching.
  """

  @enforce_keys [:id, :name]
  defstruct [
    :id,
    :name,
    :age,
    :nationality,
    :overall,
    :potential,
    :club,
    :position,
    :jersey_number,
    :preferred_foot,
    :height,
    :weight,
    :value,
    :wage
  ]

  @type t :: %__MODULE__{
          id: integer(),
          name: String.t(),
          age: integer() | nil,
          nationality: String.t() | nil,
          overall: integer() | nil,
          potential: integer() | nil,
          club: String.t() | nil,
          position: String.t() | nil,
          jersey_number: integer() | nil,
          preferred_foot: String.t() | nil,
          height: String.t() | nil,
          weight: String.t() | nil,
          value: String.t() | nil,
          wage: String.t() | nil
        }

  @doc "Builds a player from one raw CSV row (a map keyed by header names)."
  @spec from_row(map()) :: t()
  def from_row(row) do
    int = &SoccerMcp.Parse.int/1

    %__MODULE__{
      id: int.(row["ID"]),
      name: blank_to_nil(row["Name"]) || "Unknown",
      age: int.(row["Age"]),
      nationality: blank_to_nil(row["Nationality"]),
      overall: int.(row["Overall"]),
      potential: int.(row["Potential"]),
      club: blank_to_nil(row["Club"]),
      position: blank_to_nil(row["Position"]),
      jersey_number: int.(row["Jersey Number"]),
      preferred_foot: blank_to_nil(row["Preferred Foot"]),
      height: blank_to_nil(row["Height"]),
      weight: blank_to_nil(row["Weight"]),
      value: blank_to_nil(row["Value"]),
      wage: blank_to_nil(row["Wage"])
    }
  end

  defp blank_to_nil(nil), do: nil
  defp blank_to_nil(text), do: if(String.trim(text) == "", do: nil, else: String.trim(text))
end
