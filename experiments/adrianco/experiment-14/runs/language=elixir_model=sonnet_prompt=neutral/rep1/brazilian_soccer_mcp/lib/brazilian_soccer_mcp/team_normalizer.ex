defmodule BrazilianSoccerMcp.TeamNormalizer do
  @moduledoc """
  Normalizes team names across different CSV formats for consistent matching.
  """

  @state_codes ~w(AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO)

  # Known aliases mapping normalized form to canonical name
  @aliases %{
    "atletico mineiro" => "Atletico Mineiro",
    "atletico-mg" => "Atletico Mineiro",
    "atletico mg" => "Atletico Mineiro",
    "atletico pr" => "Athletico Paranaense",
    "athletico pr" => "Athletico Paranaense",
    "athletico-pr" => "Athletico Paranaense",
    "atletico paranaense" => "Athletico Paranaense",
    "atletico-paranaense" => "Athletico Paranaense",
    "sao paulo" => "Sao Paulo",
    "são paulo" => "Sao Paulo",
    "sport" => "Sport Recife",
    "sport recife" => "Sport Recife",
    "vasco da gama" => "Vasco",
    "vasco" => "Vasco",
    "coritiba" => "Coritiba",
    "gremio" => "Gremio",
    "grêmio" => "Gremio",
    "fluminense" => "Fluminense",
    "flamengo" => "Flamengo",
    "botafogo" => "Botafogo",
    "corinthians" => "Corinthians",
    "sport club corinthians paulista" => "Corinthians",
    "palmeiras" => "Palmeiras",
    "santos" => "Santos",
    "cruzeiro" => "Cruzeiro",
    "internacional" => "Internacional",
    "ceara" => "Ceara",
    "fortaleza" => "Fortaleza",
    "bahia" => "Bahia",
    "goias" => "Goias",
    "portuguesa" => "Portuguesa"
  }

  @doc """
  Normalize a team name by removing state suffixes and parenthetical notes.
  Returns a cleaned, downcased string suitable for comparison.
  """
  def normalize(name) when is_binary(name) do
    name
    |> String.trim()
    |> remove_parenthetical()
    |> remove_state_suffix()
    |> String.trim()
    |> remove_trailing_dash()
    |> String.trim()
  end

  @doc """
  Returns the canonical display name for a team (with proper casing).
  """
  def canonical(name) when is_binary(name) do
    key = normalize(name) |> String.downcase()
    Map.get(@aliases, key, normalize(name))
  end

  @doc """
  Returns true if the search term matches the team name (case-insensitive, partial match).
  """
  def matches?(team_name, search_term) do
    norm_team = team_name |> normalize() |> String.downcase()
    norm_search = search_term |> String.trim() |> String.downcase()

    # Try direct substring match first
    if String.contains?(norm_team, norm_search) do
      true
    else
      # Try without accents
      String.contains?(remove_accents(norm_team), remove_accents(norm_search))
    end
  end

  defp remove_parenthetical(name) do
    Regex.replace(~r/\s*\([^)]*\)/, name, "")
  end

  defp remove_state_suffix(name) do
    # Match patterns like "-SP", " - SP", "-RJ", etc. at end of string
    state_pattern = Enum.join(@state_codes, "|")
    regex = ~r/\s*[-–]\s*(#{state_pattern})\s*$/
    Regex.replace(regex, name, "")
  end

  defp remove_trailing_dash(name) do
    Regex.replace(~r/\s*[-–]\s*$/, name, "")
  end

  def remove_accents(str) do
    str
    |> String.replace("ã", "a")
    |> String.replace("â", "a")
    |> String.replace("á", "a")
    |> String.replace("à", "a")
    |> String.replace("ä", "a")
    |> String.replace("é", "e")
    |> String.replace("ê", "e")
    |> String.replace("è", "e")
    |> String.replace("ë", "e")
    |> String.replace("í", "i")
    |> String.replace("î", "i")
    |> String.replace("ì", "i")
    |> String.replace("ï", "i")
    |> String.replace("ó", "o")
    |> String.replace("ô", "o")
    |> String.replace("õ", "o")
    |> String.replace("ò", "o")
    |> String.replace("ö", "o")
    |> String.replace("ú", "u")
    |> String.replace("û", "u")
    |> String.replace("ù", "u")
    |> String.replace("ü", "u")
    |> String.replace("ç", "c")
    |> String.replace("ñ", "n")
  end
end
