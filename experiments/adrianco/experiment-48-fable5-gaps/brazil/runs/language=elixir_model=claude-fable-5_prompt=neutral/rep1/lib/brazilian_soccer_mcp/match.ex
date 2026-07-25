defmodule BrazilianSoccerMcp.Match do
  @moduledoc """
  A single match, normalized from any of the five match CSV files.

    * `:source`      - which file the record came from
                       (`:serie_a`, `:historical`, `:copa`, `:libertadores`, `:extended`)
    * `:competition` - `:brasileirao`, `:serie_b`, `:serie_c`, `:copa_do_brasil`,
                       `:libertadores`
    * `:home_key`/`:away_key` - canonical team keys (see `TeamNames`)
    * `:extras`      - source-specific detail (stadium, corners, shots, ...)
  """

  @enforce_keys [:source, :competition, :date, :home_key, :away_key]
  defstruct [
    :source,
    :competition,
    :date,
    :time,
    :season,
    :round,
    :stage,
    :home,
    :away,
    :home_key,
    :away_key,
    :home_goal,
    :away_goal,
    extras: %{}
  ]

  def winner_key(%__MODULE__{home_goal: hg, away_goal: ag}) when is_nil(hg) or is_nil(ag), do: nil

  def winner_key(%__MODULE__{home_goal: hg, away_goal: ag} = m) do
    cond do
      hg > ag -> m.home_key
      ag > hg -> m.away_key
      true -> :draw
    end
  end

  def margin(%__MODULE__{home_goal: hg, away_goal: ag}) when is_nil(hg) or is_nil(ag), do: 0
  def margin(%__MODULE__{home_goal: hg, away_goal: ag}), do: abs(hg - ag)
end
