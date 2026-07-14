defmodule BrazilianSoccer.Player do
  @moduledoc """
  A player record derived from the FIFA player dataset (`fifa_data.csv`).

  Only the columns relevant to the supported queries are retained. A normalized
  `club_key` is stored so players can be joined to clubs despite naming
  variations.
  """

  alias BrazilianSoccer.TeamName

  @type t :: %__MODULE__{
          id: integer() | nil,
          name: String.t() | nil,
          age: integer() | nil,
          nationality: String.t() | nil,
          overall: integer() | nil,
          potential: integer() | nil,
          club: String.t() | nil,
          club_key: String.t(),
          position: String.t() | nil,
          jersey_number: integer() | nil,
          height: String.t() | nil,
          weight: String.t() | nil
        }

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
    :jersey_number,
    :height,
    :weight
  ]

  @doc "Build a player from a FIFA CSV row (a map keyed by column header)."
  @spec from_row(map()) :: t()
  def from_row(row) when is_map(row) do
    club = field(row, "Club")

    %__MODULE__{
      id: int(row, "ID"),
      name: field(row, "Name"),
      age: int(row, "Age"),
      nationality: field(row, "Nationality"),
      overall: int(row, "Overall"),
      potential: int(row, "Potential"),
      club: club,
      club_key: if(club, do: TeamName.base(club), else: ""),
      position: field(row, "Position"),
      jersey_number: int(row, "Jersey Number"),
      height: field(row, "Height"),
      weight: field(row, "Weight")
    }
  end

  @doc "Is this a Brazilian player?"
  @spec brazilian?(t()) :: boolean()
  def brazilian?(%__MODULE__{nationality: nil}), do: false

  def brazilian?(%__MODULE__{nationality: nat}) do
    String.downcase(nat) == "brazil"
  end

  defp field(row, key) do
    case row |> Map.get(key) do
      nil -> nil
      value -> value |> to_string() |> String.trim() |> nil_if_blank()
    end
  end

  defp nil_if_blank(""), do: nil
  defp nil_if_blank(value), do: value

  defp int(row, key) do
    case field(row, key) do
      nil ->
        nil

      value ->
        case Integer.parse(value) do
          {n, _} -> n
          :error -> nil
        end
    end
  end
end
