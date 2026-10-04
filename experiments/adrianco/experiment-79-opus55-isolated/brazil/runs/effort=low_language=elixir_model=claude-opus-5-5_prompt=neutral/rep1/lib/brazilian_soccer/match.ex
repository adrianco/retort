defmodule BrazilianSoccer.Match do
  @moduledoc "A single match, unified across all source files."

  defstruct [
    :date,
    :time,
    :season,
    :competition,
    :round,
    :stage,
    :home,
    :away,
    :home_key,
    :away_key,
    :home_state,
    :away_state,
    :home_goals,
    :away_goals,
    :arena,
    :stats,
    sources: []
  ]

  def played?(%__MODULE__{home_goals: h, away_goals: a}), do: is_integer(h) and is_integer(a)
end
