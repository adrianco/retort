defmodule BrazilianSoccer.Match do
  @moduledoc """
  A played match. Team names are kept twice: `home`/`away` hold the display
  name and `home_key`/`away_key` hold the normalized key used for matching.
  """

  alias BrazilianSoccer.Normalize

  @enforce_keys [:date, :competition, :home, :away, :home_goals, :away_goals]
  defstruct [
    :date,
    :competition,
    :stage,
    :home,
    :away,
    :home_key,
    :away_key,
    :home_goals,
    :away_goals,
    :source
  ]

  @type t :: %__MODULE__{
          date: Date.t(),
          competition: binary(),
          stage: binary() | nil,
          home: binary(),
          away: binary(),
          home_key: binary(),
          away_key: binary(),
          home_goals: non_neg_integer(),
          away_goals: non_neg_integer(),
          source: binary() | nil
        }

  @doc "Builds a match from raw attributes, deriving display names and keys."
  @spec new(map()) :: t()
  def new(%{home: home, away: away} = attrs) do
    struct!(
      __MODULE__,
      Map.merge(attrs, %{
        home: Normalize.display_name(home),
        away: Normalize.display_name(away),
        home_key: Normalize.team_key(home),
        away_key: Normalize.team_key(away)
      })
    )
  end
end
