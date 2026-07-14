defmodule BrSoccer.Match do
  @moduledoc "A single normalised match record, unified across all match CSVs."

  @enforce_keys [:competition, :source, :home, :away, :home_key, :away_key]
  defstruct [
    :competition,
    :source,
    :season,
    :date,
    :round,
    :stage,
    :home,
    :away,
    :home_key,
    :away_key,
    :home_goal,
    :away_goal,
    :home_state,
    :away_state,
    :arena,
    stats: %{}
  ]

  @type t :: %__MODULE__{}

  @doc "Whether the match has a recorded final score."
  def scored?(%__MODULE__{home_goal: h, away_goal: a}), do: is_integer(h) and is_integer(a)

  @doc "Result from the home team's perspective: :home_win | :away_win | :draw | :unknown."
  def result(%__MODULE__{home_goal: h, away_goal: a}) when is_integer(h) and is_integer(a) do
    cond do
      h > a -> :home_win
      a > h -> :away_win
      true -> :draw
    end
  end

  def result(_), do: :unknown
end
