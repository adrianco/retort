defmodule BrazilianSoccerMcp.Match do
  @moduledoc """
  One played match, normalized across all source datasets.

  `home_key` and `away_key` are team keys (see `TeamName`). A key is the base
  name, qualified by state when the state is known. `home` and `away` hold
  readable names, with a state label such as "Atletico (MG)" when a base name
  is shared by several clubs.
  """

  alias BrazilianSoccerMcp.TeamName

  defstruct [
    :date,
    :competition,
    :season,
    :round,
    :home,
    :away,
    :home_key,
    :away_key,
    :home_state,
    :away_state,
    :home_goals,
    :away_goals
  ]

  @type t :: %__MODULE__{}

  @doc """
  Builds a match from raw team names. Keys start as base names and are qualified
  later by `qualify/2`. A state given in `:home_state` or `:away_state` takes
  precedence over a state suffix in the name.
  """
  @spec new(map()) :: t()
  def new(attrs) do
    attrs = Map.new(attrs)
    {home_key, home_suffix} = TeamName.parse(attrs.home)
    {away_key, away_suffix} = TeamName.parse(attrs.away)

    struct!(
      __MODULE__,
      Map.merge(attrs, %{
        home_key: home_key,
        away_key: away_key,
        home_state: Map.get(attrs, :home_state) || home_suffix,
        away_state: Map.get(attrs, :away_state) || away_suffix,
        home: TeamName.display(attrs.home),
        away: TeamName.display(attrs.away)
      })
    )
  end

  @doc """
  Maps each base name to the states seen for it across `matches`.

      %{"palmeiras" => ["SP"], "atletico" => ["MG", "PR"]}
  """
  @spec state_index([t()]) :: %{binary() => [binary()]}
  def state_index(matches) do
    matches
    |> Enum.flat_map(fn m -> [{m.home_key, m.home_state}, {m.away_key, m.away_state}] end)
    |> Enum.reject(fn {_base, state} -> is_nil(state) end)
    |> Enum.uniq()
    |> Enum.group_by(fn {base, _state} -> base end, fn {_base, state} -> state end)
  end

  @doc """
  Qualifies both teams with a state. A side without a state gets one when its
  base name has exactly one state in `index`. A side whose base name has several
  states is labelled with its state, such as "Atletico (MG)".
  """
  @spec qualify(t(), %{binary() => [binary()]}) :: t()
  def qualify(%__MODULE__{} = m, index) do
    {home_key, home} = qualify_side(m.home_key, m.home_state, m.home, index)
    {away_key, away} = qualify_side(m.away_key, m.away_state, m.away, index)

    %{m | home_key: home_key, home: home, away_key: away_key, away: away}
  end

  defp qualify_side(base, state, name, index) do
    states = Map.get(index, base, [])
    state = state || single_state(states)
    label = if state && length(states) > 1, do: "#{name} (#{state})", else: name

    {TeamName.qualify(base, state), label}
  end

  defp single_state([only]), do: only
  defp single_state(_states), do: nil
end
