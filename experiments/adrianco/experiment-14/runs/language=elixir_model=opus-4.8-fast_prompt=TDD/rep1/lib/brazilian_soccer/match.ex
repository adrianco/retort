defmodule BrazilianSoccer.Match do
  @moduledoc """
  A normalized soccer match, unified across all of the source CSV files.

  Team names are stored both as a cleaned display string (`home_team`) and as a
  canonical matching key (`home_key`). Goals are integers (or `nil` when
  unknown), dates are `Date` structs parsed from the several formats present in
  the datasets, and `season` is the 4-digit year.
  """

  alias BrazilianSoccer.TeamName

  @type t :: %__MODULE__{
          competition: String.t() | nil,
          season: integer() | nil,
          date: Date.t() | nil,
          round: String.t() | nil,
          stage: String.t() | nil,
          home_team: String.t(),
          away_team: String.t(),
          home_key: String.t(),
          away_key: String.t(),
          home_base: String.t(),
          away_base: String.t(),
          home_goals: integer() | nil,
          away_goals: integer() | nil,
          source: String.t() | nil
        }

  defstruct [
    :competition,
    :season,
    :date,
    :round,
    :stage,
    :home_team,
    :away_team,
    :home_key,
    :away_key,
    :home_base,
    :away_base,
    :home_goals,
    :away_goals,
    :source
  ]

  @doc """
  Build a match from raw attributes, normalizing names, goals, dates and season.
  """
  @spec new(keyword() | map()) :: t()
  def new(attrs) do
    attrs = Map.new(attrs)
    home = attrs |> Map.get(:home_team, "") |> to_string()
    away = attrs |> Map.get(:away_team, "") |> to_string()
    date = parse_date(Map.get(attrs, :date))

    %__MODULE__{
      competition: blank_to_nil(Map.get(attrs, :competition)),
      season: parse_season(Map.get(attrs, :season), date),
      date: date,
      round: round_to_string(Map.get(attrs, :round)),
      stage: blank_to_nil(Map.get(attrs, :stage)),
      home_team: TeamName.clean(home),
      away_team: TeamName.clean(away),
      home_key: TeamName.key(home),
      away_key: TeamName.key(away),
      home_base: TeamName.base(home),
      away_base: TeamName.base(away),
      home_goals: parse_int(Map.get(attrs, :home_goals)),
      away_goals: parse_int(Map.get(attrs, :away_goals)),
      source: blank_to_nil(Map.get(attrs, :source))
    }
  end

  @doc "Return `:home`, `:away`, `:draw`, or `nil` when the score is unknown."
  @spec winner(t()) :: :home | :away | :draw | nil
  def winner(%__MODULE__{home_goals: h, away_goals: a}) when is_integer(h) and is_integer(a) do
    cond do
      h > a -> :home
      a > h -> :away
      true -> :draw
    end
  end

  def winner(_), do: nil

  @doc "Does this match involve the given team (by fuzzy, suffix-insensitive name)?"
  @spec involves?(t(), binary()) :: boolean()
  def involves?(%__MODULE__{home_base: h, away_base: a}, team) do
    k = TeamName.base(team)
    k == h or k == a
  end

  @doc "Total goals in the match, or `nil` when the score is unknown."
  @spec total_goals(t()) :: integer() | nil
  def total_goals(%__MODULE__{home_goals: h, away_goals: a}) when is_integer(h) and is_integer(a),
    do: h + a

  def total_goals(_), do: nil

  # --- parsing helpers ---

  defp parse_int(nil), do: nil
  defp parse_int(n) when is_integer(n), do: n
  defp parse_int(n) when is_float(n), do: trunc(n)

  defp parse_int(str) when is_binary(str) do
    case str |> String.trim() |> Integer.parse() do
      {n, _rest} -> n
      :error -> nil
    end
  end

  defp parse_season(nil, %Date{year: year}), do: year
  defp parse_season(nil, _), do: nil
  defp parse_season(n, _) when is_integer(n), do: n

  defp parse_season(str, date) when is_binary(str) do
    case parse_int(str) do
      nil -> parse_season(nil, date)
      n -> n
    end
  end

  @doc false
  def parse_date(nil), do: nil

  def parse_date(value) when is_binary(value) do
    case String.trim(value) do
      "" -> nil
      trimmed -> do_parse_date(trimmed)
    end
  end

  defp do_parse_date(str) do
    # Take the date portion before any time component.
    date_part = str |> String.split([" ", "T"], parts: 2) |> hd()

    cond do
      String.contains?(date_part, "/") -> parse_br_date(date_part)
      String.contains?(date_part, "-") -> parse_iso_date(date_part)
      true -> nil
    end
  end

  defp parse_iso_date(str) do
    case Date.from_iso8601(str) do
      {:ok, date} -> date
      _ -> nil
    end
  end

  defp parse_br_date(str) do
    with [d, m, y] <- String.split(str, "/"),
         {day, _} <- Integer.parse(d),
         {month, _} <- Integer.parse(m),
         {year, _} <- Integer.parse(y),
         {:ok, date} <- Date.new(year, month, day) do
      date
    else
      _ -> nil
    end
  end

  defp round_to_string(nil), do: nil
  defp round_to_string(n) when is_integer(n), do: Integer.to_string(n)

  defp round_to_string(str) when is_binary(str) do
    case String.trim(str) do
      "" -> nil
      other -> other
    end
  end

  defp blank_to_nil(nil), do: nil

  defp blank_to_nil(str) when is_binary(str) do
    case String.trim(str) do
      "" -> nil
      other -> other
    end
  end

  defp blank_to_nil(other), do: other
end
