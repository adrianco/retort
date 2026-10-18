defmodule SoccerMcp.Match do
  @moduledoc """
  A single played match, normalized across all match datasets.

  `home_key` and `away_key` are `SoccerMcp.Team.key/1` values used for
  matching. `home` and `away` are display names. `home_state` and
  `away_state` are lowercase state codes (or `nil` when unknown). `stage`
  holds the cup round or tournament stage ("final", "semifinals", "group
  stage") when the source provides one.
  """

  alias SoccerMcp.Team

  @enforce_keys [:date, :competition, :season, :home, :away, :home_goals, :away_goals]
  defstruct [
    :date,
    :competition,
    :season,
    :stage,
    :home,
    :away,
    :home_key,
    :away_key,
    :home_state,
    :away_state,
    :home_goals,
    :away_goals,
    :source
  ]

  @type t :: %__MODULE__{
          date: Date.t(),
          competition: String.t(),
          season: integer(),
          stage: String.t() | nil,
          home: String.t(),
          away: String.t(),
          home_key: String.t(),
          away_key: String.t(),
          home_state: String.t() | nil,
          away_state: String.t() | nil,
          home_goals: non_neg_integer(),
          away_goals: non_neg_integer(),
          source: String.t() | nil
        }

  @competitions [
    "Brasileirão Série A",
    "Brasileirão Série B",
    "Brasileirão Série C",
    "Copa do Brasil",
    "Copa Libertadores"
  ]

  @doc "The canonical competition names used in results."
  def competitions, do: @competitions

  @doc """
  Builds a match from raw team names, a date, scores and metadata.

  Options: `:stage`, `:source`, and `:home_state` / `:away_state` for a state
  code given by a source column. When omitted, the state is read from the
  team name's suffix.

      iex> m = SoccerMcp.Match.new("Flamengo-RJ", "Fluminense-RJ", ~D[2023-09-03], 2, 1, "Brasileirão Série A", 2023)
      iex> {m.home, m.home_key, m.home_goals, m.home_state}
      {"Flamengo", "flamengo", 2, "rj"}
  """
  def new(home, away, date, home_goals, away_goals, competition, season, opts \\ []) do
    %__MODULE__{
      date: date,
      competition: competition,
      season: season,
      stage: blank_to_nil(opts[:stage]),
      home: Team.display(home),
      away: Team.display(away),
      home_key: Team.key(home),
      away_key: Team.key(away),
      home_state: opts[:home_state] || Team.state(home),
      away_state: opts[:away_state] || Team.state(away),
      home_goals: home_goals,
      away_goals: away_goals,
      source: opts[:source]
    }
  end

  @doc """
  Maps a free-text competition name to a canonical competition, or `nil`
  when the text does not name one.

      iex> SoccerMcp.Match.canonical_competition("brasileirao")
      "Brasileirão Série A"
      iex> SoccerMcp.Match.canonical_competition("Copa do Brasil")
      "Copa do Brasil"
      iex> SoccerMcp.Match.canonical_competition("libertadores")
      "Copa Libertadores"
  """
  @spec canonical_competition(String.t() | nil) :: String.t() | nil
  def canonical_competition(nil), do: nil

  def canonical_competition(text) do
    folded = SoccerMcp.Parse.fold(text)

    cond do
      folded == "" -> nil
      String.contains?(folded, "libertador") -> "Copa Libertadores"
      String.contains?(folded, "copa do brasil") -> "Copa do Brasil"
      String.contains?(folded, "serie b") -> "Brasileirão Série B"
      String.contains?(folded, "serie c") -> "Brasileirão Série C"
      String.contains?(folded, "serie a") -> "Brasileirão Série A"
      String.contains?(folded, "brasileir") -> "Brasileirão Série A"
      true -> nil
    end
  end

  @doc "True when the team with `key` played in this match, home or away."
  def involves?(%__MODULE__{} = match, key) do
    Team.matches?(match.home_key, key) or Team.matches?(match.away_key, key)
  end

  @doc "Goals scored and conceded from the perspective of the team with `key`."
  def goals_for_against(%__MODULE__{} = match, key) do
    if Team.matches?(match.home_key, key) do
      {match.home_goals, match.away_goals}
    else
      {match.away_goals, match.home_goals}
    end
  end

  @doc """
  The state code of the side with `key`, or `nil` when unknown. Used to tell
  apart clubs with the same short name in different states.
  """
  def side_state(%__MODULE__{} = match, key) do
    if Team.matches?(match.home_key, key), do: match.home_state, else: match.away_state
  end

  @doc "True when the team with `key` was at home in this match."
  def home_for?(%__MODULE__{} = match, key), do: Team.matches?(match.home_key, key)

  defp blank_to_nil(nil), do: nil
  defp blank_to_nil(text), do: if(String.trim(text) == "", do: nil, else: String.trim(text))
end
