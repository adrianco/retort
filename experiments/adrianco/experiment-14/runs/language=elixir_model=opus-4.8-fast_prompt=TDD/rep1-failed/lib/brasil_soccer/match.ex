defmodule BrasilSoccer.Match do
  @moduledoc """
  A single match in a unified shape, regardless of which source file it came
  from. Team names are stored both as cleaned display strings and as comparison
  keys (see `BrasilSoccer.Normalize`), and the winner is derived from the
  scoreline.
  """

  alias BrasilSoccer.Normalize

  @enforce_keys []
  defstruct competition: nil,
            season: nil,
            round: nil,
            stage: nil,
            date: nil,
            home_team: nil,
            away_team: nil,
            home_key: nil,
            away_key: nil,
            home_goal: nil,
            away_goal: nil,
            home_state: nil,
            away_state: nil,
            winner: nil,
            source: nil

  @type result :: :win | :loss | :draw
  @type t :: %__MODULE__{}

  @doc "Build a match from canonical attributes, normalising names and scoreline."
  @spec new(map()) :: t()
  def new(attrs) do
    home = attrs[:home_team]
    away = attrs[:away_team]
    home_display = home && Normalize.team_name(home)
    away_display = away && Normalize.team_name(away)

    %__MODULE__{
      competition: attrs[:competition],
      season: attrs[:season],
      round: attrs[:round],
      stage: attrs[:stage],
      date: attrs[:date],
      home_team: home_display,
      away_team: away_display,
      home_key: home && Normalize.key(home),
      away_key: away && Normalize.key(away),
      home_goal: attrs[:home_goal],
      away_goal: attrs[:away_goal],
      home_state: attrs[:home_state],
      away_state: attrs[:away_state],
      source: attrs[:source],
      winner: winner(attrs[:home_goal], attrs[:away_goal])
    }
  end

  @doc "True when `team` is either side of the match (fuzzy, normalised)."
  @spec involves?(t(), String.t()) :: boolean()
  def involves?(%__MODULE__{} = m, team) do
    side(m, team) != nil
  end

  @doc """
  The result from `team`'s perspective: `:win`, `:loss`, `:draw`, or `nil` when
  the team is not in the match or the score is unknown.
  """
  @spec result_for(t(), String.t()) :: result() | nil
  def result_for(%__MODULE__{winner: nil}, _team), do: nil

  def result_for(%__MODULE__{} = m, team) do
    case {side(m, team), m.winner} do
      {nil, _} -> nil
      {_, :draw} -> :draw
      {:home, :home} -> :win
      {:away, :away} -> :win
      _ -> :loss
    end
  end

  @doc "Which side `team` is on: `:home`, `:away`, or `nil`."
  @spec side(t(), String.t()) :: :home | :away | nil
  def side(%__MODULE__{} = m, team) do
    cond do
      m.home_team && Normalize.matches?(m.home_team, team) -> :home
      m.away_team && Normalize.matches?(m.away_team, team) -> :away
      true -> nil
    end
  end

  defp winner(h, a) when is_integer(h) and is_integer(a) do
    cond do
      h > a -> :home
      a > h -> :away
      true -> :draw
    end
  end

  defp winner(_, _), do: nil
end
