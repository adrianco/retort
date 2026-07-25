defmodule BrazilianSoccer.Query.Filters do
  @moduledoc """
  Argument coercion shared by every query module.

  MCP arguments arrive as JSON, so seasons may be `2019` or `"2019"`,
  competitions may be `"Brasileirão"`, `"serie a"` or `:serie_a`, and dates may
  be ISO or Brazilian.  Everything funnels through here so the query modules
  can assume clean values.
  """

  alias BrazilianSoccer.Data.Graph
  alias BrazilianSoccer.Dates
  alias BrazilianSoccer.Names

  @competition_aliases %{
    "serie a" => :serie_a,
    "seriea" => :serie_a,
    "a" => :serie_a,
    "brasileirao" => :serie_a,
    "brasileirao serie a" => :serie_a,
    "campeonato brasileiro" => :serie_a,
    "campeonato brasileiro serie a" => :serie_a,
    "brazilian league" => :serie_a,
    "league" => :serie_a,
    "serie b" => :serie_b,
    "serieb" => :serie_b,
    "b" => :serie_b,
    "brasileirao serie b" => :serie_b,
    "serie c" => :serie_c,
    "seriec" => :serie_c,
    "c" => :serie_c,
    "copa do brasil" => :copa_do_brasil,
    "copa brasil" => :copa_do_brasil,
    "brazilian cup" => :copa_do_brasil,
    "cup" => :copa_do_brasil,
    "copa" => :copa_do_brasil,
    "libertadores" => :libertadores,
    "copa libertadores" => :libertadores,
    "conmebol libertadores" => :libertadores
  }

  @doc """
  Normalise a competition argument.

  Returns `{:ok, atom}`, `{:ok, nil}` when nothing was asked for, or
  `{:error, {:unknown_competition, value, known}}`.
  """
  @spec competition(any) :: {:ok, atom | nil} | {:error, tuple}
  def competition(nil), do: {:ok, nil}
  def competition(""), do: {:ok, nil}

  def competition(value) when is_atom(value) do
    if Graph.competition(value), do: {:ok, value}, else: competition(Atom.to_string(value))
  end

  def competition(value) when is_binary(value) do
    key = value |> Names.ascii() |> String.downcase() |> String.replace(~r/[^a-z ]/u, " ")
    key = key |> String.split() |> Enum.join(" ")

    case Map.fetch(@competition_aliases, key) do
      {:ok, id} ->
        {:ok, id}

      :error ->
        {:error, {:unknown_competition, value, Enum.map(Graph.competitions(), & &1.id)}}
    end
  end

  def competition(value), do: {:error, {:unknown_competition, value, []}}

  @doc "Normalise a season argument (`2019`, `\"2019\"`, `nil`)."
  @spec season(any) :: {:ok, integer | nil} | {:error, tuple}
  def season(nil), do: {:ok, nil}
  def season(""), do: {:ok, nil}
  def season(value) when is_integer(value), do: {:ok, value}

  def season(value) when is_binary(value) do
    case Integer.parse(String.trim(value)) do
      {year, _} -> {:ok, year}
      :error -> {:error, {:invalid_season, value}}
    end
  end

  def season(value), do: {:error, {:invalid_season, value}}

  @doc "Normalise a list of seasons."
  @spec seasons(any) :: {:ok, [integer]} | {:error, tuple}
  def seasons(nil), do: {:ok, []}

  def seasons(values) when is_list(values) do
    Enum.reduce_while(values, {:ok, []}, fn value, {:ok, acc} ->
      case season(value) do
        {:ok, nil} -> {:cont, {:ok, acc}}
        {:ok, year} -> {:cont, {:ok, acc ++ [year]}}
        {:error, reason} -> {:halt, {:error, reason}}
      end
    end)
  end

  def seasons(value) do
    case season(value) do
      {:ok, nil} -> {:ok, []}
      {:ok, year} -> {:ok, [year]}
      error -> error
    end
  end

  @doc "Normalise a date argument."
  @spec date(any) :: {:ok, Date.t() | nil} | {:error, tuple}
  def date(nil), do: {:ok, nil}
  def date(""), do: {:ok, nil}
  def date(%Date{} = date), do: {:ok, date}

  def date(value) when is_binary(value) do
    case Dates.to_date(value) do
      nil -> {:error, {:invalid_date, value}}
      date -> {:ok, date}
    end
  end

  def date(value), do: {:error, {:invalid_date, value}}

  @doc "Resolve a team name, or `{:ok, nil}` when none was supplied."
  @spec team(Graph.t(), any) :: {:ok, BrazilianSoccer.Model.Team.t() | nil} | {:error, tuple}
  def team(_graph, nil), do: {:ok, nil}
  def team(_graph, ""), do: {:ok, nil}

  def team(graph, name) when is_binary(name) do
    case Graph.find_team(graph, name) do
      {:ok, team} -> {:ok, team}
      {:error, reason} -> {:error, reason}
    end
  end

  def team(_graph, value), do: {:error, {:invalid_team, value}}

  @unlimited 10_000_000

  @doc """
  Clamp a limit argument into `1..max`.

  `:all` (used by internal callers that must aggregate over every row before
  the caller truncates for display) bypasses the cap.
  """
  @spec limit(any, pos_integer, pos_integer) :: pos_integer
  def limit(value, default \\ 20, max \\ 500)
  def limit(nil, default, _max), do: default
  def limit(:all, _default, _max), do: @unlimited

  def limit(value, default, max) when is_binary(value) do
    case Integer.parse(value) do
      {int, _} -> limit(int, default, max)
      :error -> default
    end
  end

  def limit(value, _default, max) when is_integer(value) and value > 0, do: min(value, max)
  def limit(_value, default, _max), do: default

  @doc "Coerce a boolean-ish argument."
  @spec boolean(any, boolean) :: boolean
  def boolean(nil, default), do: default
  def boolean(value, _default) when is_boolean(value), do: value
  def boolean("true", _default), do: true
  def boolean("false", _default), do: false
  def boolean(_value, default), do: default

  @doc "Coerce an integer-ish argument, or `nil`."
  @spec integer(any) :: integer | nil
  def integer(nil), do: nil
  def integer(value) when is_integer(value), do: value
  def integer(value) when is_float(value), do: round(value)

  def integer(value) when is_binary(value) do
    case Integer.parse(String.trim(value)) do
      {int, _} -> int
      :error -> nil
    end
  end

  def integer(_), do: nil

  @doc "Coerce a `venue` argument into `:home | :away | :all`."
  @spec venue(any) :: {:ok, :home | :away | :all} | {:error, tuple}
  def venue(nil), do: {:ok, :all}
  def venue(""), do: {:ok, :all}
  def venue(value) when value in [:home, :away, :all], do: {:ok, value}

  def venue(value) when is_binary(value) do
    case String.downcase(String.trim(value)) do
      "home" -> {:ok, :home}
      "away" -> {:ok, :away}
      "all" -> {:ok, :all}
      "any" -> {:ok, :all}
      "overall" -> {:ok, :all}
      "total" -> {:ok, :all}
      "both" -> {:ok, :all}
      other -> {:error, {:invalid_venue, other}}
    end
  end

  def venue(value), do: {:error, {:invalid_venue, value}}

  @doc """
  Convert string keys to (existing) atom keys so argument maps can be merged
  regardless of whether they came from JSON or from Elixir code.
  """
  @spec atomize(map) :: map
  def atomize(args) when is_map(args) do
    Map.new(args, fn
      {key, value} when is_binary(key) -> {to_existing_atom(key), value}
      pair -> pair
    end)
  end

  defp to_existing_atom(key) do
    String.to_existing_atom(key)
  rescue
    ArgumentError -> key
  end

  @doc "Fetch a key from a map that may use string or atom keys."
  @spec get(map, atom, any) :: any
  def get(args, key, default \\ nil) when is_map(args) and is_atom(key) do
    case Map.fetch(args, key) do
      {:ok, value} -> value
      :error -> Map.get(args, Atom.to_string(key), default)
    end
  end
end
