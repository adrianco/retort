defmodule BrazilianSoccerMcp.TeamName do
  @moduledoc """
  Normalizes Brazilian club names so one team matches across all datasets.

  The sources spell the same club differently: `"Palmeiras-SP"`,
  `"Palmeiras - SP"`, `"Palmeiras"`, `"Sociedade Esportiva Palmeiras"`,
  `"Nacional (URU)"`, `"São Paulo"` and `"Sao Paulo"`.

  A team key is the normalized base name, optionally qualified by state as
  `"base|STATE"`. The state separates clubs that share a name, such as
  Atlético-MG and Athletico-PR, which both normalize to "atletico". See
  `parse/1`, `qualify/2`, `base/1` and `state/1`.
  """

  # Normalized variant -> canonical base. Covers names that the state rule
  # alone cannot merge. Remaining splits are listed in the README.
  @aliases %{
    "sport club corinthians paulista" => "corinthians",
    "sociedade esportiva palmeiras" => "palmeiras",
    "clube de regatas do flamengo" => "flamengo",
    "cr flamengo" => "flamengo",
    "sao paulo futebol clube" => "sao paulo",
    "sao paulo fc" => "sao paulo",
    "athletico" => "atletico",
    "athletico paranaense" => "atletico",
    "atletico paranaense" => "atletico",
    "atletico mineiro" => "atletico",
    "botafogo rj" => "botafogo",
    "america mg" => "america",
    "gremio rs" => "gremio",
    "coritiba pr" => "coritiba",
    "cuiaba mt" => "cuiaba",
    "fortaleza ec" => "fortaleza",
    "fortaleza fc" => "fortaleza",
    "vasco da gama" => "vasco",
    "vasco da gama rj" => "vasco",
    "ec bahia" => "bahia"
  }

  @doc """
  Splits a club name into `{base_key, state}`. `state` is the two-letter code
  from a `-SP` or ` - RJ` suffix, or `nil`.
  """
  @spec parse(binary()) :: {binary(), binary() | nil}
  def parse(name) when is_binary(name) do
    base = name |> strip_notes() |> normalize()
    {Map.get(@aliases, base, base), state_suffix(name)}
  end

  @doc "Base key for a club name, ignoring state. Used to match FIFA club names."
  @spec key(binary()) :: binary()
  def key(name) when is_binary(name), do: name |> parse() |> elem(0)

  @doc "Adds a state qualifier to a base key. `nil` leaves the base unchanged."
  @spec qualify(binary(), binary() | nil) :: binary()
  def qualify(base, nil), do: base
  def qualify(base, state), do: "#{base}|#{state}"

  @doc "Base part of a team key (`\"atletico|mg\"` -> `\"atletico\"`)."
  @spec base(binary()) :: binary()
  def base(key), do: key |> String.split("|", parts: 2) |> hd()

  @doc "State part of a team key (`\"atletico|mg\"` -> `\"mg\"`), or `nil`."
  @spec state(binary()) :: binary() | nil
  def state(key) do
    case String.split(key, "|", parts: 2) do
      [_base, state] -> state
      [_base] -> nil
    end
  end

  @doc "Readable club name with state suffix and parenthetical notes removed."
  @spec display(binary()) :: binary()
  def display(name) when is_binary(name), do: strip_notes(name)

  @doc "Lowercases, removes accents and collapses punctuation to single spaces."
  @spec normalize(binary()) :: binary()
  def normalize(text) when is_binary(text) do
    text
    |> strip_accents()
    |> String.downcase()
    |> String.replace(~r/[^a-z0-9]+/, " ")
    |> String.trim()
  end

  @doc "Removes combining accent marks after NFD decomposition (São -> Sao)."
  @spec strip_accents(binary()) :: binary()
  def strip_accents(text) when is_binary(text) do
    text
    |> :unicode.characters_to_nfd_binary()
    |> String.replace(~r/\p{Mn}/u, "")
  end

  # Drops "(URU)" style notes and trailing state codes such as "-SP" or " - RJ".
  defp strip_notes(name) do
    name
    |> String.replace(~r/\([^)]*\)/, " ")
    |> String.replace(~r/\s*-\s*[A-Z]{2,3}\s*$/, "")
    |> String.replace(~r/\s+/, " ")
    |> String.trim()
  end

  # Two-letter codes only, so country codes such as "-EQU" or "-URU" are ignored.
  defp state_suffix(name) do
    case Regex.run(~r/\s*-\s*([A-Z]{2})\s*$/, name) do
      [_, state] -> state
      nil -> nil
    end
  end
end
