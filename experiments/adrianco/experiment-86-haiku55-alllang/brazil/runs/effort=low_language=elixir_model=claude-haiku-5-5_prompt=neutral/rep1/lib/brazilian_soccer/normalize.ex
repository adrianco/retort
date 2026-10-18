defmodule BrazilianSoccer.Normalize do
  @moduledoc """
  Text normalization used to match query strings against dataset values.

  * `fold/1` removes accents and case, and collapses punctuation to spaces.
  * `display_name/1` strips the state suffix (`"Palmeiras-SP"`) and
    parenthetical notes (`"Nacional (URU)"`, `"(antigo ...)"`).
  * `team_key/1` gives the canonical key used to compare teams, applying a
    small alias table for long official names.
  """

  # Clubs that share a base name and differ only by state. The state is kept
  # for these lookups, because stripping it would merge the clubs. Keys are
  # folded names including the state code.
  @state_qualified_aliases %{
    "atletico pr" => "athletico",
    "atletico go" => "atletico goianiense",
    "fluminense pi" => "fluminense piaui"
  }

  # Folded keys (see fold/1) mapped to the key used everywhere else.
  @team_aliases %{
    "sport club corinthians paulista" => "corinthians",
    "sociedade esportiva palmeiras" => "palmeiras",
    "clube de regatas do flamengo" => "flamengo",
    "sao paulo futebol clube" => "sao paulo",
    "clube atletico mineiro" => "atletico",
    "atletico mineiro" => "atletico",
    "atletico paranaense" => "athletico",
    "athletico paranaense" => "athletico",
    "clube de regatas vasco da gama" => "vasco",
    "vasco da gama" => "vasco",
    "gremio foot ball porto alegrense" => "gremio",
    "esporte clube bahia" => "bahia",
    "fortaleza esporte clube" => "fortaleza",
    "river plate" => "river",
    "c r b" => "crb",
    "sport recife" => "sport",
    "serra f c" => "serra",
    "red bull bragantino" => "bragantino"
  }

  @doc "Lowercases, strips accents and replaces punctuation with single spaces."
  @spec fold(binary()) :: binary()
  def fold(text) when is_binary(text) do
    text
    |> :unicode.characters_to_nfd_binary()
    |> String.replace(~r/\p{Mn}+/u, "")
    |> String.downcase()
    |> String.replace(~r/[^\p{L}\p{N}]+/u, " ")
    |> String.trim()
  end

  defp strip_parentheticals(name), do: String.replace(name, ~r/\([^)]*\)/u, " ")

  @doc """
  Removes parenthetical notes, the trailing state or country code, and
  leading/trailing club-type words (`EC`, `FC`, ...), keeping the original
  accents and capitalization.

      iex> BrazilianSoccer.Normalize.display_name("Palmeiras-SP")
      "Palmeiras"
      iex> BrazilianSoccer.Normalize.display_name("Nacional (URU)")
      "Nacional"
      iex> BrazilianSoccer.Normalize.display_name("EC Bahia")
      "Bahia"
      iex> BrazilianSoccer.Normalize.display_name("Vasco Da Gama RJ")
      "Vasco Da Gama"
  """
  @spec display_name(binary()) :: binary()
  def display_name(name) when is_binary(name) do
    name
    |> strip_parentheticals()
    |> String.replace(
      ~r/[\s-]+(?:AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO|[A-Z]{3})\s*$/u,
      ""
    )
    |> String.replace(~r/\s+(?:FC|EC|AC|SC|SE|AA)\s*$/u, "")
    |> String.replace(~r/^(?:EC|SC|CR|SE|AA|FC|AC)\s+(?=\S)/u, "")
    |> String.replace(~r/\s+/u, " ")
    |> String.trim()
  end

  @doc """
  Canonical comparison key for a team name.

      iex> BrazilianSoccer.Normalize.team_key("São Paulo-SP")
      "sao paulo"
      iex> BrazilianSoccer.Normalize.team_key("Sport Club Corinthians Paulista")
      "corinthians"
  """
  @spec team_key(binary()) :: binary()
  def team_key(name) when is_binary(name) do
    qualified = name |> strip_parentheticals() |> fold()

    case Map.fetch(@state_qualified_aliases, qualified) do
      {:ok, key} ->
        key

      :error ->
        key = name |> display_name() |> fold()
        Map.get(@team_aliases, key, key)
    end
  end

  @doc """
  Parses an integer from a CSV cell. Accepts `"2"` and `"2.0"` (the latter
  appears in some files). Returns `nil` for blank or non-numeric input.
  """
  @spec integer(term()) :: integer() | nil
  def integer(value) when is_integer(value), do: value
  def integer(value) when is_float(value), do: trunc(value)

  def integer(value) when is_binary(value) do
    text = String.trim(value)

    case Integer.parse(text) do
      {n, ""} ->
        n

      _ ->
        case Float.parse(text) do
          {f, ""} -> trunc(f)
          _ -> nil
        end
    end
  end

  def integer(_), do: nil
end
