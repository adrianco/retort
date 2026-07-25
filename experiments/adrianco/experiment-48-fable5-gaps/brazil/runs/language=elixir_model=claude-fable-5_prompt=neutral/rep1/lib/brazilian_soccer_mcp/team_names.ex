defmodule BrazilianSoccerMcp.TeamNames do
  @moduledoc """
  Team name normalization.

  The datasets spell the same club many ways: "Palmeiras-SP", "Palmeiras",
  "América - MG", "America MG", "A.s.a. - AL", "Atlético Mineiro",
  "Atletico-MG", "Vasco da Gama-RJ" / "Vasco", etc. This module reduces every
  spelling to a canonical `key` (e.g. `"palmeiras-sp"`, `"america-mg"`) so
  matches from different files can be joined, deduplicated, and aggregated.

  Normalization steps:
    1. strip parentheticals (keeping a country code such as "(URU)" as state)
    2. split a trailing state/country suffix ("-SP", " - MG", " RJ", "-EQU")
    3. remove accents, downcase, drop punctuation
    4. apply an alias table ("atletico mineiro" -> {"atletico", "MG"})
    5. fill in a default home state for well-known clubs written without one
  """

  @states ~w(AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO)
  # Data errors seen in the wild: "BH" used for Bahia.
  @state_fixes %{"BH" => "BA"}
  @countries ~w(ARG BOL CHI COL ECU EQU MEX PAR PER URU VEN USA)

  # Applied to the cleaned base name. Value is {canonical_base, state_or_nil};
  # the alias state is only used when the name carried no explicit state.
  @base_aliases %{
    "atletico mineiro" => {"atletico", "MG"},
    "america mineiro" => {"america", "MG"},
    "athletico paranaense" => {"athletico", "PR"},
    "atletico paranaense" => {"athletico", "PR"},
    "athletico" => {"athletico", "PR"},
    "atletico goianiense" => {"atletico", "GO"},
    "atletico clube goianiense" => {"atletico", "GO"},
    "vasco da gama" => {"vasco", "RJ"},
    "vasco" => {"vasco", "RJ"},
    "red bull bragantino" => {"bragantino", "SP"},
    "america de natal" => {"america", "RN"},
    "america fc natal" => {"america", "RN"},
    "ceara sporting club" => {"ceara", "CE"},
    "sport club do recife" => {"sport", "PE"},
    "sport recife" => {"sport", "PE"},
    "sport club corinthians paulista" => {"corinthians", "SP"},
    "sao paulo fc" => {"sao paulo", "SP"},
    "se palmeiras" => {"palmeiras", "SP"},
    "gremio fb porto alegrense" => {"gremio", "RS"},
    "abc" => {"abc", "RN"},
    "csa" => {"csa", "AL"},
    "crb" => {"crb", "AL"},
    "asa" => {"asa", "AL"}
  }

  # Home state assumed for famous clubs when the dataset omits it, so that
  # "Flamengo" and "Flamengo-RJ" produce the same key.
  @default_states %{
    "flamengo" => "RJ",
    "fluminense" => "RJ",
    "botafogo" => "RJ",
    "americano" => "RJ",
    "corinthians" => "SP",
    "palmeiras" => "SP",
    "santos" => "SP",
    "sao paulo" => "SP",
    "portuguesa" => "SP",
    "ponte preta" => "SP",
    "guarani" => "SP",
    "santo andre" => "SP",
    "sao caetano" => "SP",
    "bragantino" => "SP",
    "ituano" => "SP",
    "mirassol" => "SP",
    "novorizontino" => "SP",
    "barueri" => "SP",
    "gremio prudente" => "SP",
    "gremio" => "RS",
    "internacional" => "RS",
    "juventude" => "RS",
    "brasil de pelotas" => "RS",
    "cruzeiro" => "MG",
    "ipatinga" => "MG",
    "tombense" => "MG",
    "coritiba" => "PR",
    "parana" => "PR",
    "londrina" => "PR",
    "operario" => "PR",
    "bahia" => "BA",
    "vitoria" => "BA",
    "sport" => "PE",
    "nautico" => "PE",
    "santa cruz" => "PE",
    "ceara" => "CE",
    "fortaleza" => "CE",
    "goias" => "GO",
    "vila nova" => "GO",
    "avai" => "SC",
    "chapecoense" => "SC",
    "figueirense" => "SC",
    "criciuma" => "SC",
    "joinville" => "SC",
    "brusque" => "SC",
    "cuiaba" => "MT",
    "paysandu" => "PA",
    "remo" => "PA",
    "brasiliense" => "DF",
    "sampaio correa" => "MA",
    "confianca" => "SE"
  }

  @doc """
  Normalize a raw team name (optionally with a state hint from a separate
  column) into `%{key, base, state, display}`.
  """
  def normalize(raw, state_hint \\ nil) do
    name = raw |> to_string() |> String.trim()
    {name, paren_state} = extract_parenthetical(name)
    {name, suffix_state} = split_suffix(name)
    base = clean(name)
    state = suffix_state || paren_state || normalize_state(state_hint)

    {base, state} =
      case Map.fetch(@base_aliases, base) do
        {:ok, {abase, astate}} ->
          {abase, state || astate}

        :error ->
          # "Fortaleza FC" / "EC Juventude" -> "fortaleza" / "juventude"
          stripped = strip_club_words(base)

          case Map.fetch(@base_aliases, stripped) do
            {:ok, {abase, astate}} -> {abase, state || astate}
            :error -> {stripped, state}
          end
      end

    state = state || Map.get(@default_states, base)

    # Atlético-PR renamed itself Athletico; unify the two spellings.
    base = if base == "atletico" and state == "PR", do: "athletico", else: base

    %{
      key: if(state, do: "#{base}-#{String.downcase(state)}", else: base),
      base: base,
      state: state,
      display: name
    }
  end

  # Remove generic club-type words that some datasets add ("EC Juventude",
  # "Fortaleza FC", "Ceará Sporting Club"); keep the name if nothing remains.
  defp strip_club_words(base) do
    stripped =
      base
      |> String.replace(~r/\b(esporte clube|futebol clube|sporting club)\b/, " ")
      |> String.split(" ", trim: true)
      |> Enum.reject(&(&1 in ["ec", "fc"]))
      |> Enum.join(" ")

    if stripped == "", do: base, else: stripped
  end

  @doc "Remove accents, downcase, and strip punctuation from a name."
  def clean(s) do
    s
    |> String.normalize(:nfd)
    |> String.replace(~r/\p{Mn}/u, "")
    |> String.downcase()
    |> String.replace(".", "")
    |> String.replace(~r/[^a-z0-9]+/u, " ")
    |> String.trim()
  end

  # "Nacional (URU)" -> {"Nacional", "URU"}; other parentheticals are dropped.
  defp extract_parenthetical(name) do
    case Regex.run(~r/^(.*?)\s*\(([A-Za-z]{2,4})\)\s*$/u, name) do
      [_, rest, code] ->
        code = String.upcase(code)
        if code in @countries, do: {rest, code}, else: {strip_parens(name), nil}

      nil ->
        {strip_parens(name), nil}
    end
  end

  defp strip_parens(name),
    do: name |> String.replace(~r/\s*\([^)]*\)/u, "") |> String.trim()

  # "Palmeiras-SP" / "América - MG" / "America MG" / "Barcelona-EQU"
  defp split_suffix(name) do
    cond do
      m = Regex.run(~r/^(.*?)\s*[-–]\s*([A-Za-z]{2,3})$/u, name) ->
        [_, rest, code] = m
        take_suffix(name, rest, code)

      m = Regex.run(~r/^(.*\S)\s+([A-Z]{2})$/u, name) ->
        [_, rest, code] = m
        take_suffix(name, rest, code)

      true ->
        {name, nil}
    end
  end

  defp take_suffix(original, rest, code) do
    case normalize_state(code) do
      nil -> {original, nil}
      state -> {String.trim(rest), state}
    end
  end

  @doc "Default home state assumed for a well-known base name, or nil."
  def default_state(base), do: Map.get(@default_states, base)

  @doc "Validate/normalize a state or country code; returns nil when unknown."
  def normalize_state(nil), do: nil
  def normalize_state(""), do: nil

  def normalize_state(code) do
    code = code |> to_string() |> String.trim() |> String.upcase()
    code = Map.get(@state_fixes, code, code)
    if code in @states or code in @countries, do: code, else: nil
  end
end
