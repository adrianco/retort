defmodule SoccerMcp.Team do
  @moduledoc """
  Team name normalization.

  The source datasets name the same club differently: with a state suffix
  ("Palmeiras-SP"), with a parenthesised country or former name
  ("Nacional (URU)"), with its full legal name ("Sport Club Corinthians
  Paulista"), or with accents and mixed case ("Grêmio", "GREMIO").

  `key/1` reduces every variant to one lowercase ASCII key. `state/1` reads
  the Brazilian state code (UF) when the name carries one, so clubs that
  share a short name, such as Atlético-MG and Atlético-GO, stay apart.
  `matches?/2` lets a query such as "Corinthians" match a stored key on
  whole-word boundaries.
  """

  # Full names that do not reduce to the short form on their own.
  @aliases %{
    "sport club corinthians paulista" => "corinthians",
    "sociedade esportiva palmeiras" => "palmeiras",
    "clube de regatas do flamengo" => "flamengo",
    "sao paulo futebol clube" => "sao paulo",
    "sport club internacional" => "internacional",
    "gremio foot ball porto alegrense" => "gremio",
    "clube atletico mineiro" => "atletico",
    "atletico mineiro" => "atletico",
    "atletico paranaense" => "athletico",
    "athletico paranaense" => "athletico",
    "fluminense football club" => "fluminense",
    "cruzeiro esporte clube" => "cruzeiro",
    "sport club do recife" => "sport",
    "sport recife" => "sport",
    "vasco da gama" => "vasco",
    "ec bahia" => "bahia"
  }

  @uf_codes ~w(ac al ap am ba ce df es go ma mt ms mg pa pb pr pe pi rj rn rs ro rr sc sp se to)
  @uf_alternation Enum.join(@uf_codes, "|")

  @doc """
  Returns the normalized key for a raw team name.

      iex> SoccerMcp.Team.key("Palmeiras-SP")
      "palmeiras"
      iex> SoccerMcp.Team.key("América - MG")
      "america"
  """
  @spec key(String.t()) :: String.t()
  def key(name) when is_binary(name) do
    base =
      name
      |> strip_parenthesised()
      |> strip_name_suffix()
      |> strip_accents()
      |> String.downcase()
      |> String.replace(~r/[^a-z0-9]+/, " ")
      |> String.trim()
      |> strip_club_suffix()
      |> strip_uf_word()
      |> then(&Map.get(@aliases, &1, &1))

    # Some sources write Atlético-PR as "Atletico-PR"; it is "Athletico" everywhere else.
    if base == "atletico" and state(name) == "pr", do: "athletico", else: base
  end

  @doc """
  Returns the display name: the raw name without its state or country suffix.

      iex> SoccerMcp.Team.display("Flamengo-RJ")
      "Flamengo"
  """
  @spec display(String.t()) :: String.t()
  def display(name) when is_binary(name) do
    name
    |> strip_parenthesised()
    |> strip_name_suffix()
    |> String.trim()
  end

  @doc """
  The lowercase Brazilian state code (UF) a name ends with, or `nil`.

      iex> SoccerMcp.Team.state("Atlético - MG")
      "mg"
      iex> SoccerMcp.Team.state("Flamengo")
      nil
  """
  @spec state(String.t() | nil) :: String.t() | nil
  def state(nil), do: nil

  def state(name) when is_binary(name) do
    case Regex.run(~r/(?:\s*-\s*|\s+)(#{@uf_alternation})\s*$/iu, strip_parenthesised(name)) do
      [_, uf] -> String.downcase(uf)
      nil -> nil
    end
  end

  @doc """
  True when two state codes do not contradict each other. A missing state
  (`nil`) is compatible with any state.
  """
  @spec compatible_states?(String.t() | nil, String.t() | nil) :: boolean()
  def compatible_states?(a, b), do: is_nil(a) or is_nil(b) or a == b

  @doc """
  True when a stored team key satisfies a query key.

  Equal keys match. Otherwise the query must appear as a whole-word
  sequence inside the stored key, so "corinthians" matches "corinthians" and
  "recife" matches "sport recife", but "pau" does not match "sao paulo".
  """
  @spec matches?(String.t(), String.t()) :: boolean()
  def matches?(stored_key, query_key) when is_binary(stored_key) and is_binary(query_key) do
    query_key != "" and
      (stored_key == query_key or
         String.contains?(" " <> stored_key <> " ", " " <> query_key <> " "))
  end

  # "4 de Julho EC" and "4 de Julho" are the same club. A bare "EC" or "FC"
  # with nothing before it is left alone.
  defp strip_club_suffix(key), do: String.replace(key, ~r/^(.+) (ec|fc|sc|ac|af)$/, "\\1")

  # "Audax SP" and "Botafogo RJ": a state code written as a plain word.
  # Only stripped when a name precedes it.
  defp strip_uf_word(key), do: String.replace(key, ~r/^(.+) (#{@uf_alternation})$/, "\\1")

  defp strip_parenthesised(name), do: String.replace(name, ~r/\([^)]*\)/u, " ")

  # Trailing "-SP", " - RJ", "-EQU" style suffixes (state or country code).
  defp strip_name_suffix(name), do: String.replace(name, ~r/\s*-\s*[A-Za-z]{2,3}\s*$/u, "")

  defp strip_accents(text) do
    text
    |> :unicode.characters_to_nfd_binary()
    |> String.replace(~r/\p{Mn}/u, "")
  end
end
