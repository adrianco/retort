defmodule BrazilianSoccerMcp.TeamNormalizer do
  @moduledoc """
  Normalizes team names across the various CSV datasets.

  Strips state suffixes (e.g. "Palmeiras-SP" -> "Palmeiras"),
  maps known full/alternate names to canonical short names,
  and provides fuzzy matching for user queries.
  """

  # Maps alternate or full names to a canonical short name
  @aliases %{
    "sport club corinthians paulista" => "Corinthians",
    "corinthians paulista" => "Corinthians",
    "sociedade esportiva palmeiras" => "Palmeiras",
    "flamengo" => "Flamengo",
    "clube de regatas do flamengo" => "Flamengo",
    "fluminense football club" => "Fluminense",
    "club de regatas vasco da gama" => "Vasco",
    "cr vasco da gama" => "Vasco",
    "santos futebol clube" => "Santos",
    "sport club internacional" => "Internacional",
    "gremio foot-ball porto alegrense" => "Grêmio",
    "gremio" => "Grêmio",
    "grêmio" => "Grêmio",
    "atletico mineiro" => "Atlético-MG",
    "atlético mineiro" => "Atlético-MG",
    "clube atletico mineiro" => "Atlético-MG",
    "atletico-mg" => "Atlético-MG",
    "atletico mg" => "Atlético-MG",
    "atletico paranaense" => "Atlético-PR",
    "atletico-pr" => "Atlético-PR",
    "club athletico paranaense" => "Atlético-PR",
    "sport club do recife" => "Sport Recife",
    "sao paulo futebol clube" => "São Paulo",
    "são paulo futebol clube" => "São Paulo",
    "sao paulo" => "São Paulo",
    "são paulo" => "São Paulo",
    "cruzeiro esporte clube" => "Cruzeiro",
    "botafogo de futebol e regatas" => "Botafogo",
    "america mineiro" => "América-MG",
    "américa mineiro" => "América-MG",
    "america-mg" => "América-MG",
    "america mg" => "América-MG",
    "ceara sporting club" => "Ceará",
    "cearã" => "Ceará",
    "fortaleza esporte clube" => "Fortaleza",
    "bragantino" => "Bragantino",
    "red bull bragantino" => "Bragantino",
    "rb bragantino" => "Bragantino",
    "bahia" => "Bahia",
    "esporte clube bahia" => "Bahia",
    "cuiaba esporte clube" => "Cuiabá",
    "cuiabá" => "Cuiabá",
    "juventude" => "Juventude",
    "esporte clube juventude" => "Juventude",
    "goias esporte clube" => "Goiás",
    "goias" => "Goiás",
    "goiás" => "Goiás",
    "chapecoense" => "Chapecoense",
    "associacao chapecoense de futebol" => "Chapecoense",
    "avai futebol clube" => "Avaí",
    "avai" => "Avaí",
    "avaí" => "Avaí",
    "coritiba foot ball club" => "Coritiba",
    "coritiba" => "Coritiba",
    "criciuma esporte clube" => "Criciúma",
    "criciuma" => "Criciúma",
    "criciúma" => "Criciúma",
    "ponte preta" => "Ponte Preta",
    "associacao atletica ponte preta" => "Ponte Preta",
    "vitoria" => "Vitória",
    "esporte clube vitoria" => "Vitória",
    "vitória" => "Vitória",
    "sport club" => "Sport Recife",
    "portuguesa" => "Portuguesa",
    "associacao portuguesa de desportos" => "Portuguesa",
    "nautico" => "Náutico",
    "clube nautico capibaribe" => "Náutico",
    "náutico" => "Náutico",
    "figueirense" => "Figueirense",
    "figueirense futebol clube" => "Figueirense",
    "guarani" => "Guarani",
    "guarani futebol clube" => "Guarani"
  }

  @doc """
  Normalize a team name: strip state suffix, apply canonical aliases.
  Returns the canonical name (or the cleaned input if no alias found).
  """
  def normalize(nil), do: nil
  def normalize(""), do: ""

  def normalize(name) when is_binary(name) do
    name
    |> strip_state_suffix()
    |> apply_alias()
  end

  @doc """
  Returns true if query matches a normalized team name (case-insensitive, partial).
  """
  def matches?(team_name, query) when is_binary(team_name) and is_binary(query) do
    if String.trim(team_name) == "" or String.trim(query) == "" do
      false
    else
      normalized_team = normalize(team_name) |> String.downcase()
      normalized_query = normalize(query) |> String.downcase()

      String.contains?(normalized_team, normalized_query) or
        String.contains?(normalized_query, normalized_team) or
        String.contains?(team_name |> String.downcase(), normalized_query)
    end
  end

  # Strip " - STATE" or "-STATE" suffix (e.g. "Palmeiras-SP", "Flamengo - RJ")
  defp strip_state_suffix(name) do
    Regex.replace(~r/\s*-\s*[A-Z]{2}$/, name, "")
  end

  defp apply_alias(name) do
    key = name |> String.downcase() |> String.trim()
    Map.get(@aliases, key, name)
  end
end
