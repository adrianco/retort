defmodule BrSoccer.Team do
  @moduledoc """
  Team name normalization. Maps the many spellings in the datasets
  ("Palmeiras-SP", "Flamengo - RJ", "Atlético Mineiro", "Gremio RS",
  "Sport Club Corinthians Paulista") onto one canonical key.
  """

  @states ~w(ac al ap am ba ce df es go ma mt ms mg pa pb pr pe pi rj rn rs ro rr sc sp se to)
  # Base names shared by several clubs: keep the state to disambiguate.
  @ambiguous ~w(atletico america botafogo)

  @aliases %{
    "athletico" => "atletico pr",
    "athletico paranaense" => "atletico pr",
    "atletico paranaense" => "atletico pr",
    "atletico mineiro" => "atletico mg",
    "atletico goianiense" => "atletico go",
    "america mineiro" => "america mg",
    "america de natal" => "america rn",
    "america fc natal" => "america rn",
    "vasco da gama" => "vasco",
    "cr vasco da gama" => "vasco",
    "sport recife" => "sport",
    "sport club do recife" => "sport",
    "sport club corinthians paulista" => "corinthians",
    "sc corinthians paulista" => "corinthians",
    "sao paulo fc" => "sao paulo",
    "se palmeiras" => "palmeiras",
    "cr flamengo" => "flamengo",
    "clube de regatas do flamengo" => "flamengo",
    "fluminense fc" => "fluminense",
    "santos fc" => "santos",
    "gremio fbpa" => "gremio",
    "red bull bragantino" => "bragantino",
    "rb bragantino" => "bragantino",
    "botafogo" => "botafogo rj",
    "portuguesa desportos" => "portuguesa",
    "chapecoense af" => "chapecoense",
    "ec bahia" => "bahia",
    "fortaleza esporte clube" => "fortaleza",
    "fortaleza ec" => "fortaleza",
    "fortaleza fc" => "fortaleza"
  }

  @display %{
    "sao paulo" => "São Paulo",
    "gremio" => "Grêmio",
    "atletico mg" => "Atlético-MG",
    "atletico pr" => "Athletico-PR",
    "atletico go" => "Atlético-GO",
    "america mg" => "América-MG",
    "america rn" => "América-RN",
    "botafogo rj" => "Botafogo",
    "avai" => "Avaí",
    "goias" => "Goiás",
    "ceara" => "Ceará",
    "criciuma" => "Criciúma",
    "cuiaba" => "Cuiabá",
    "parana" => "Paraná",
    "vitoria" => "Vitória"
  }

  @rivalries [
    {"flamengo", "fluminense", "Fla-Flu"},
    {"flamengo", "vasco", "Clássico dos Milhões"},
    {"flamengo", "botafogo rj", "Clássico da Rivalidade"},
    {"fluminense", "vasco", "Clássico dos Gigantes"},
    {"botafogo rj", "fluminense", "Clássico Vovô"},
    {"botafogo rj", "vasco", "Clássico da Amizade"},
    {"corinthians", "palmeiras", "Derby Paulista"},
    {"corinthians", "sao paulo", "Majestoso"},
    {"corinthians", "santos", "Clássico Alvinegro"},
    {"palmeiras", "sao paulo", "Choque-Rei"},
    {"palmeiras", "santos", "Clássico da Saudade"},
    {"santos", "sao paulo", "San-São"},
    {"gremio", "internacional", "Grenal"},
    {"atletico mg", "cruzeiro", "Clássico Mineiro"},
    {"atletico pr", "coritiba", "Atletiba"},
    {"bahia", "vitoria", "Ba-Vi"},
    {"ceara", "fortaleza", "Clássico-Rei"},
    {"nautico", "sport", "Clássico dos Clássicos"},
    {"santa cruz", "sport", "Clássico das Multidões"},
    {"goias", "vila nova", "Clássico Goiano"}
  ]

  @doc "Returns the canonical key for a raw team name."
  def canonical(nil), do: ""

  def canonical(name) do
    cleaned =
      name
      |> ascii()
      |> String.downcase()
      |> String.replace(~r/\(.*?\)/, " ")
      |> String.replace(~r/[^a-z0-9 ]/, " ")
      |> String.split()

    {base, state} =
      case Enum.reverse(cleaned) do
        [last | rest] when last in @states and rest != [] -> {Enum.reverse(rest), last}
        _ -> {cleaned, nil}
      end

    full = Enum.join(base, " ")
    base = if Map.has_key?(@aliases, full), do: full, else: base |> strip_affixes() |> Enum.join(" ")

    cond do
      Map.has_key?(@aliases, base) and not (base in @ambiguous and state != nil) -> @aliases[base]
      base in @ambiguous and state != nil -> base <> " " <> state
      base == "athletico" -> "atletico pr"
      true -> base
    end
  end

  @prefixes ~w(ec fc sc ca se cr ac)
  @suffixes ~w(fc ec sc ac)

  # "EC Juventude" -> juventude, "Santa Cruz FC" -> santa cruz
  defp strip_affixes([p | rest]) when p in @prefixes and rest != [], do: strip_affixes(rest)

  defp strip_affixes(words) do
    case Enum.reverse(words) do
      [s | rest] when s in @suffixes and rest != [] -> Enum.reverse(rest)
      _ -> words
    end
  end

  @doc "Strips diacritics (São -> Sao)."
  def ascii(str) do
    str
    |> String.normalize(:nfd)
    |> String.replace(~r/\p{Mn}/u, "")
  end

  @doc "Does a canonical team key match a user-supplied query?"
  def matches?(key, query) do
    q = canonical(query)
    q != "" and (key == q or (q in @ambiguous and String.starts_with?(key, q <> " ")))
  end

  @doc "Pretty display name for a canonical key."
  def display(key) do
    Map.get_lazy(@display, key, fn ->
      key |> String.split() |> Enum.map_join(" ", &capitalize/1)
    end)
  end

  defp capitalize(w) when w in @states, do: String.upcase(w)
  defp capitalize(w) when w in ~w(de da do das dos), do: w
  defp capitalize(w), do: String.capitalize(w)

  @doc "Returns the derby name if the two teams are traditional rivals."
  def derby(a, b) do
    Enum.find_value(@rivalries, fn {x, y, name} ->
      if {x, y} == {a, b} or {x, y} == {b, a}, do: name
    end)
  end
end
