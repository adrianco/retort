defmodule BrazilianSoccer.Names do
  @moduledoc """
  Team / club name normalisation.

  The six Kaggle datasets spell the same club in wildly different ways:

      "Palmeiras-SP"      "Palmeiras"          "Palmeiras - SP"
      "Atlético - MG"     "Atletico Mineiro"   "Atlético-MG"
      "Sport-PE"          "Sport Recife"       "Sport Club do Recife"
      "Nacional (URU)"    "Nacional AM"

  `parse/1` turns any of those spellings into

      %{raw: ..., base: "atletico", attr: "mg", attr_kind: :state, display: "Atlético-MG"}

  `base` is an accent-free, punctuation-free, club-suffix-free name and `attr`
  is the state (Brazilian clubs) or country (foreign clubs) qualifier when the
  source spelled one out.

  The final team id is *not* decided here: whether "botafogo" needs to become
  "botafogo-rj" depends on whether the corpus also contains a Botafogo from
  another state.  `BrazilianSoccer.Data.Graph` makes that call from the parsed
  occurrences (see `resolve_keys/1`).
  """

  @states %{
    "ac" => "Acre",
    "al" => "Alagoas",
    "am" => "Amazonas",
    "ap" => "Amapá",
    "ba" => "Bahia",
    "ce" => "Ceará",
    "df" => "Distrito Federal",
    "es" => "Espírito Santo",
    "go" => "Goiás",
    "ma" => "Maranhão",
    "mg" => "Minas Gerais",
    "ms" => "Mato Grosso do Sul",
    "mt" => "Mato Grosso",
    "pa" => "Pará",
    "pb" => "Paraíba",
    "pe" => "Pernambuco",
    "pi" => "Piauí",
    "pr" => "Paraná",
    "rj" => "Rio de Janeiro",
    "rn" => "Rio Grande do Norte",
    "ro" => "Rondônia",
    "rr" => "Roraima",
    "rs" => "Rio Grande do Sul",
    "sc" => "Santa Catarina",
    "se" => "Sergipe",
    "sp" => "São Paulo",
    "to" => "Tocantins"
  }

  @state_names Map.new(@states, fn {code, name} ->
                 {name
                  |> :unicode.characters_to_nfd_binary()
                  |> :unicode.characters_to_binary()
                  |> String.replace(~r/[\x{0300}-\x{036F}]/u, "")
                  |> String.downcase(), code}
               end)

  @countries %{
    "arg" => "Argentina",
    "bol" => "Bolivia",
    "bra" => "Brazil",
    "chi" => "Chile",
    "col" => "Colombia",
    "equ" => "Ecuador",
    "mex" => "Mexico",
    "par" => "Paraguay",
    "per" => "Peru",
    "uru" => "Uruguay",
    "ven" => "Venezuela"
  }

  # Multi word club-type phrases removed before anything else.
  @phrases [
    "esporte clube",
    "esportes clube",
    "futebol clube",
    "sport club",
    "sporting club",
    "clube de regatas",
    "clube atletico",
    "clube de futebol",
    "associacao desportiva",
    "associacao atletica",
    "sociedade esportiva",
    "gremio esportivo"
  ]

  # Standalone abbreviations / club words that carry no identity.
  @generic ~w(fc ec sc ac cr se ad ae ca cs ge aa af sa futebol clube club esporte
              esportes sociedade associacao desportiva desportos atletica sporting)

  @edge_words ~w(do de da dos das)

  # name (already ascii/downcased/punctuation-collapsed) => {base, attr}
  @aliases %{
    "athletico paranaense" => {"athletico", "pr"},
    "atletico paranaense" => {"athletico", "pr"},
    "athletico" => {"athletico", "pr"},
    "atletico mineiro" => {"atletico", "mg"},
    "atletico goianiense" => {"atletico", "go"},
    "atletico acreano" => {"atletico", "ac"},
    "atletico alagoinhas" => {"atletico", "ba"},
    "atletico cearense" => {"atletico cearense", "ce"},
    "uniclinic" => {"atletico cearense", "ce"},
    "vasco" => {"vasco da gama", "rj"},
    "vasco da gama" => {"vasco da gama", "rj"},
    "sport recife" => {"sport", "pe"},
    "sport club do recife" => {"sport", "pe"},
    "sport do recife" => {"sport", "pe"},
    "recife" => {"sport", "pe"},
    "nautico capibaribe" => {"nautico", "pe"},
    "red bull bragantino" => {"bragantino", "sp"},
    "portuguesa desportos" => {"portuguesa", "sp"},
    "ceara sporting club" => {"ceara", "ce"},
    "ceara sporting" => {"ceara", "ce"},
    "america fc minas gerais" => {"america", "mg"},
    "america fc natal" => {"america", "rn"},
    "america natal" => {"america", "rn"},
    "clube do remo" => {"remo", "pa"},
    "remo" => {"remo", "pa"},
    "gremio foot ball porto alegrense" => {"gremio", "rs"},
    "sao paulo futebol clube" => {"sao paulo", "sp"},
    "cr flamengo" => {"flamengo", "rj"},
    "flamengo rio" => {"flamengo", "rj"},
    "santos futebol clube" => {"santos", "sp"},
    "moto clube" => {"moto", "ma"},
    "moto club de sao luis" => {"moto", "ma"},
    "athletic club" => {"athletic", "mg"},
    "sport club corinthians paulista" => {"corinthians", "sp"},
    "sociedade esportiva palmeiras" => {"palmeiras", "sp"},
    "botafogo de futebol e regatas" => {"botafogo", "rj"},
    "fluminense de feira" => {"fluminense de feira", "ba"},
    "nautico" => {"nautico", "pe"}
  }

  # Applied after `base`/`attr` are known: Atlético-PR is spelled both ways,
  # but it is the same club as Athletico Paranaense.
  @base_attr_aliases %{
    {"atletico", "pr"} => {"athletico", "pr"},
    {"atletico", "mineiro"} => {"atletico", "mg"}
  }

  # Fallback state for bases the corpus leaves ambiguous.
  @default_attr %{
    "america" => "mg",
    "atletico" => "mg",
    "athletico" => "pr",
    "botafogo" => "rj",
    "bragantino" => "sp",
    "flamengo" => "rj",
    "fluminense" => "rj",
    "guarani" => "sp",
    "internacional" => "rs",
    "juventude" => "rs",
    "nautico" => "pe",
    "portuguesa" => "sp",
    "santa cruz" => "pe",
    "santos" => "sp",
    "sport" => "pe",
    "vitoria" => "ba"
  }

  # Pretty display names for the clubs the datasets talk about most.
  @display %{
    "america-mg" => "América-MG",
    "america-rn" => "América-RN",
    "athletico" => "Athletico Paranaense",
    "athletico-pr" => "Athletico Paranaense",
    "atletico-go" => "Atlético Goianiense",
    "atletico-mg" => "Atlético Mineiro",
    "avai" => "Avaí",
    "bahia" => "Bahia",
    "botafogo-rj" => "Botafogo",
    "botafogo-sp" => "Botafogo-SP",
    "botafogo-pb" => "Botafogo-PB",
    "bragantino-sp" => "Red Bull Bragantino",
    "ceara" => "Ceará",
    "chapecoense" => "Chapecoense",
    "corinthians" => "Corinthians",
    "coritiba" => "Coritiba",
    "criciuma" => "Criciúma",
    "cruzeiro" => "Cruzeiro",
    "cuiaba" => "Cuiabá",
    "flamengo" => "Flamengo",
    "flamengo-rj" => "Flamengo",
    "fluminense-rj" => "Fluminense",
    "fortaleza" => "Fortaleza",
    "goias" => "Goiás",
    "gremio" => "Grêmio",
    "guarani" => "Guarani",
    "figueirense" => "Figueirense",
    "joinville" => "Joinville",
    "santo andre" => "Santo André",
    "sao caetano" => "São Caetano",
    "internacional-rs" => "Internacional",
    "juventude-rs" => "Juventude",
    "nautico" => "Náutico",
    "nautico-pe" => "Náutico",
    "palmeiras" => "Palmeiras",
    "parana" => "Paraná",
    "ponte preta" => "Ponte Preta",
    "portuguesa-sp" => "Portuguesa",
    "santa cruz-pe" => "Santa Cruz",
    "santos-sp" => "Santos",
    "sao paulo" => "São Paulo",
    "sport" => "Sport Recife",
    "sport-pe" => "Sport Recife",
    "vasco da gama" => "Vasco da Gama",
    "vasco da gama-rj" => "Vasco da Gama",
    "vitoria-ba" => "Vitória"
  }

  @doc "Strip accents/diacritics, returning plain ASCII."
  @spec ascii(binary) :: binary
  def ascii(string) when is_binary(string) do
    string
    |> :unicode.characters_to_nfd_binary()
    |> :unicode.characters_to_binary()
    |> String.replace(~r/[\x{0300}-\x{036F}]/u, "")
  end

  @doc "State code => full state name (\"mg\" => \"Minas Gerais\")."
  def state_name(code) when is_binary(code), do: Map.get(@states, String.downcase(code))
  def state_name(_), do: nil

  @doc "Country code => country name (\"uru\" => \"Uruguay\")."
  def country_name(code) when is_binary(code), do: Map.get(@countries, String.downcase(code))
  def country_name(_), do: nil

  def state?(code), do: is_binary(code) and Map.has_key?(@states, String.downcase(code))
  def country?(code), do: is_binary(code) and Map.has_key?(@countries, String.downcase(code))

  @doc """
  Parse a raw team spelling into `%{raw:, base:, attr:, attr_kind:}`.

      iex> BrazilianSoccer.Names.parse("Palmeiras-SP").base
      "palmeiras"
      iex> BrazilianSoccer.Names.parse("Atlético Mineiro").attr
      "mg"
  """
  @spec parse(binary | nil) :: map | nil
  def parse(nil), do: nil

  def parse(raw) when is_binary(raw) do
    trimmed = raw |> String.trim() |> String.trim("\"") |> String.trim()

    if trimmed == "" do
      nil
    else
      {without_parens, paren_attr} = extract_parentheticals(ascii(trimmed) |> String.downcase())

      tokens = tokenize(without_parens)
      {tokens, suffix_attr} = extract_suffix(tokens)

      attr = paren_attr || suffix_attr
      joined = Enum.join(tokens, " ")

      {base, attr} =
        case Map.fetch(@aliases, joined) do
          {:ok, {b, a}} ->
            {b, attr || a}

          :error ->
            cleaned = strip_generic(tokens)
            cleaned_joined = Enum.join(cleaned, " ")

            case Map.fetch(@aliases, cleaned_joined) do
              {:ok, {b, a}} -> {b, attr || a}
              :error -> {cleaned_joined, attr}
            end
        end

      base = if base == "", do: joined, else: base
      {base, attr} = Map.get(@base_attr_aliases, {base, attr}, {base, attr})

      %{
        raw: trimmed,
        base: base,
        attr: attr,
        attr_kind: attr_kind(attr),
        display: trimmed
      }
    end
  end

  defp attr_kind(nil), do: nil

  defp attr_kind(attr) do
    cond do
      Map.has_key?(@states, attr) -> :state
      Map.has_key?(@countries, attr) -> :country
      true -> nil
    end
  end

  defp extract_parentheticals(string) do
    Regex.scan(~r/\(([^)]*)\)/u, string)
    |> Enum.reduce({string, nil}, fn [full, inner], {acc, attr} ->
      inner = String.trim(inner)

      code =
        cond do
          Map.has_key?(@countries, inner) -> inner
          Map.has_key?(@states, inner) -> inner
          Map.has_key?(@state_names, inner) -> Map.fetch!(@state_names, inner)
          true -> nil
        end

      {String.replace(acc, full, " "), attr || code}
    end)
  end

  defp tokenize(string) do
    string
    |> String.replace(~r/[^a-z0-9]+/u, " ")
    |> String.split(" ", trim: true)
    |> merge_initials()
  end

  # "a b c" (from "A.B.C.") -> "abc"
  defp merge_initials(tokens) do
    tokens
    |> Enum.chunk_by(&(String.length(&1) == 1))
    |> Enum.flat_map(fn
      [single | _] = chunk when byte_size(single) == 1 and length(chunk) > 1 -> [Enum.join(chunk)]
      chunk -> chunk
    end)
  end

  defp extract_suffix(tokens) when length(tokens) < 2, do: {tokens, nil}

  defp extract_suffix(tokens) do
    last = List.last(tokens)

    if Map.has_key?(@states, last) or Map.has_key?(@countries, last) do
      {Enum.drop(tokens, -1), last}
    else
      {tokens, nil}
    end
  end

  defp strip_generic(tokens) do
    joined = Enum.join(tokens, " ")

    without_phrases =
      Enum.reduce(@phrases, joined, fn phrase, acc -> String.replace(acc, phrase, " ") end)

    cleaned =
      without_phrases
      |> String.split(" ", trim: true)
      |> Enum.reject(&(&1 in @generic))
      |> trim_edge_words()

    if cleaned == [], do: tokens, else: cleaned
  end

  defp trim_edge_words([]), do: []

  defp trim_edge_words(tokens) do
    tokens =
      case tokens do
        [first | rest] when first in @edge_words -> rest
        other -> other
      end

    case Enum.reverse(tokens) do
      [last | rest] when last in @edge_words -> Enum.reverse(rest)
      _ -> tokens
    end
  end

  @doc """
  Turn parsed occurrences into canonical team ids.

  Takes a list of `parse/1` results and returns `%{{base, attr} => key}`.  A
  base that shows up with more than one state/country keeps the qualifier
  ("botafogo-rj", "botafogo-sp"); anything unambiguous stays bare
  ("palmeiras").  Occurrences with no qualifier fall back to the configured
  default state, then to the most frequent one.
  """
  @spec resolve_keys([map]) :: %{optional({binary, binary | nil}) => binary}
  def resolve_keys(parsed) do
    by_base =
      Enum.reduce(parsed, %{}, fn %{base: base, attr: attr}, acc ->
        Map.update(acc, base, %{attr => 1}, fn counts ->
          Map.update(counts, attr, 1, &(&1 + 1))
        end)
      end)

    Enum.reduce(by_base, %{}, fn {base, counts}, acc ->
      attrs = counts |> Map.keys() |> Enum.reject(&is_nil/1)

      case attrs do
        [] ->
          Map.put(acc, {base, nil}, base)

        [_single] when map_size(counts) <= 2 and length(attrs) == 1 ->
          # one qualifier (plus possibly bare spellings) => everything is one club
          Enum.reduce(Map.keys(counts), acc, fn attr, acc -> Map.put(acc, {base, attr}, base) end)

        _ ->
          fallback = default_attr(base, counts, attrs)

          Enum.reduce(Map.keys(counts), acc, fn
            nil, acc -> Map.put(acc, {base, nil}, "#{base}-#{fallback}")
            attr, acc -> Map.put(acc, {base, attr}, "#{base}-#{attr}")
          end)
      end
    end)
  end

  defp default_attr(base, counts, attrs) do
    configured = Map.get(@default_attr, base)

    if configured in attrs do
      configured
    else
      attrs
      |> Enum.max_by(fn attr -> Map.fetch!(counts, attr) end)
    end
  end

  @doc """
  Human friendly name for a canonical key, given the raw spellings seen.

  Prefers the curated name, then an accented spelling from the data, then the
  shortest raw spelling.
  """
  @spec display_name(binary, [binary]) :: binary
  def display_name(key, raw_variants) do
    case Map.fetch(@display, key) do
      {:ok, name} ->
        name

      :error ->
        variants = Enum.uniq(raw_variants)
        accented = Enum.filter(variants, &(&1 != ascii(&1)))
        pool = if accented == [], do: variants, else: accented

        case pool do
          [] -> key |> String.split(" ") |> Enum.map_join(" ", &String.capitalize/1)
          _ -> Enum.min_by(pool, &String.length/1)
        end
    end
  end

  @doc "Normalised search form of a user supplied query string."
  @spec search_key(binary) :: binary
  def search_key(query) when is_binary(query) do
    case parse(query) do
      nil -> ""
      %{base: base} -> base
    end
  end

  @doc """
  Similarity in `0.0..1.0` between a normalised query (`a`) and a normalised
  candidate name (`b`).

  A query that is part of the name ("fla" → "flamengo") scores high.  The
  reverse — the name being part of the query — only scores high when the name
  covers most of the query, so that "Real Madrid" does not match the Brazilian
  club "Real".
  """
  @spec similarity(binary, binary) :: float
  def similarity(a, b) do
    cond do
      a == b -> 1.0
      a == "" or b == "" -> 0.0
      String.starts_with?(b, a) -> 0.95
      String.contains?(b, a) -> 0.9
      String.contains?(a, b) and String.length(b) * 5 >= String.length(a) * 3 -> 0.88
      true -> String.jaro_distance(a, b)
    end
  end
end
