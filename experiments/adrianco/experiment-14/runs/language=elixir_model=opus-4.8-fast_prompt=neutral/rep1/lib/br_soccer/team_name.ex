defmodule BrSoccer.TeamName do
  @moduledoc """
  Team-name normalisation.

  The datasets refer to the same club in many ways:

    * with a state suffix — `"Palmeiras-SP"`, `"Flamengo-RJ"`, `"Botafogo RJ"`
    * with a state/country in parentheses — `"Nacional (URU)"`
    * with accents or without — `"São Paulo"` vs `"Sao Paulo"`, `"Grêmio"`
    * with full descriptive names — `"Athletico Paranaense"` vs `"Atletico-PR"`

  We derive two things from a raw name:

    * `key/1` — a canonical, accent-free, lower-case match key used to decide
      whether two raw names refer to the same club. Cross-file matching relies
      on this (e.g. a FIFA `Club` and a match `home_team`).
    * `display/1` — a clean, human-friendly name for output.

  Most clubs collapse on their bare name (so `"Flamengo"` and `"Flamengo-RJ"`
  match across files). A small set of genuinely ambiguous bases — clubs that
  exist in several states — keep the state in their key so that, say,
  Atlético-MG and Atlético-PR stay distinct.
  """

  # Brazilian state (UF) codes used as suffixes.
  @states ~w(AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO)

  # Bare names shared by clubs in several states — keep the state in the key.
  @ambiguous ~w(atletico america botafogo)

  # Regional adjectives that imply a state, for sources that spell it out.
  @region_to_uf %{
    "mineiro" => "MG",
    "paranaense" => "PR",
    "goianiense" => "GO",
    "goiano" => "GO",
    "paulista" => "SP",
    "carioca" => "RJ",
    "gaucho" => "RS",
    "baiano" => "BA",
    "cearense" => "CE",
    "pernambucano" => "PE",
    "catarinense" => "SC"
  }

  # Maps a raw joined "core" to a canonical core. Lets descriptive names from
  # the FIFA dataset collapse onto the short forms used in the match files.
  @aliases %{
    "sportrecife" => "sport",
    "cearasporting" => "ceara",
    "americaminasgerais" => "americamg",
    "americaminas" => "americamg",
    "vascogama" => "vasco",
    "redbullbragantino" => "bragantino",
    "rbbragantino" => "bragantino",
    "athleticparanaense" => "atleticopr"
  }

  # Curated display names for well-known clubs, keyed by canonical key.
  @display %{
    "flamengo" => "Flamengo",
    "fluminense" => "Fluminense",
    "palmeiras" => "Palmeiras",
    "corinthians" => "Corinthians",
    "santos" => "Santos",
    "saopaulo" => "São Paulo",
    "gremio" => "Grêmio",
    "internacional" => "Internacional",
    "cruzeiro" => "Cruzeiro",
    "vasco" => "Vasco da Gama",
    "atleticomg" => "Atlético-MG",
    "atleticopr" => "Athletico-PR",
    "atleticogo" => "Atlético-GO",
    "americamg" => "América-MG",
    "botafogorj" => "Botafogo-RJ",
    "bahia" => "Bahia",
    "fortaleza" => "Fortaleza",
    "ceara" => "Ceará",
    "coritiba" => "Coritiba",
    "chapecoense" => "Chapecoense",
    "goias" => "Goiás",
    "bragantino" => "Red Bull Bragantino",
    "cuiaba" => "Cuiabá",
    "avai" => "Avaí",
    "sport" => "Sport Recife",
    "csa" => "CSA",
    "vitoria" => "Vitória",
    "parana" => "Paraná",
    "criciuma" => "Criciúma",
    "vascodagama" => "Vasco da Gama"
  }

  @doc "Strip a leading/trailing whitespace-normalised version of `raw`."
  @spec clean(binary()) :: binary()
  def clean(raw) do
    raw
    |> to_string()
    |> String.trim()
    |> String.replace(~r/\s+/u, " ")
  end

  @doc """
  Canonical match key for a raw team name.

  Accent-free, lower-case, alphanumeric only. State is appended only for
  ambiguous bases so most variants of a club collapse together.
  """
  @spec key(binary()) :: binary()
  def key(raw) do
    {base, state} = split_state(clean(raw))

    tokens =
      base
      |> deaccent()
      |> String.downcase()
      |> String.replace("athletico", "atletico")
      |> String.replace(~r/[^a-z0-9 ]/u, "")
      |> String.split(" ", trim: true)
      |> drop_noise()

    # A regional adjective both supplies the state and is dropped from the base.
    {core_tokens, region_state} =
      Enum.reduce(tokens, {[], nil}, fn tok, {acc, st} ->
        case Map.get(@region_to_uf, tok) do
          nil -> {[tok | acc], st}
          uf -> {acc, st || uf}
        end
      end)

    core =
      core_tokens
      |> Enum.reverse()
      |> Enum.join()
      |> apply_alias()

    state = state || region_state

    cond do
      core == "" -> deaccent(base) |> String.downcase() |> String.replace(~r/[^a-z0-9]/u, "")
      core in @ambiguous and state != nil -> core <> String.downcase(state)
      true -> core
    end
  end

  defp apply_alias(core), do: Map.get(@aliases, core, core)

  @doc "Human-friendly display name for a raw team name."
  @spec display(binary()) :: binary()
  def display(raw) do
    k = key(raw)

    case Map.get(@display, k) do
      nil -> base_display(raw)
      name -> name
    end
  end

  @doc "True when two raw names refer to the same club."
  @spec same?(binary(), binary()) :: boolean()
  def same?(a, b), do: key(a) == key(b)

  # ---- helpers ----

  defp base_display(raw) do
    {base, _state} = split_state(clean(raw))
    base
  end

  # Pull a trailing state/country marker off the name, returning {base, uf|nil}.
  defp split_state(name) do
    cond do
      # "Team (URU)" / "Team (SP)"
      match = Regex.run(~r/^(.*?)\s*\(([A-Za-z]{2,4})\)\s*$/u, name) ->
        [_, base, code] = match
        {String.trim(base), state_or_nil(code)}

      # "Team - MG" / "Team-MG" / "Team MG"
      match = Regex.run(~r/^(.*?)[\s\-]+([A-Za-z]{2})$/u, name) ->
        [_, base, code] = match
        up = String.upcase(code)

        if up in @states and String.trim(base) != "" do
          {String.trim(base), up}
        else
          {name, nil}
        end

      true ->
        {name, nil}
    end
  end

  defp state_or_nil(code) do
    up = String.upcase(code)
    if up in @states, do: up, else: nil
  end

  # Generic corporate/legal tokens that do not help identify a club. Note that
  # "sport" is deliberately NOT here: Sport (Recife) uses it as its identity.
  @noise ~w(fc ec sc ac cf esporte clube futebol sporting associacao atletica
            de da do dos das e the)
  defp drop_noise(tokens) do
    case Enum.reject(tokens, &(&1 in @noise)) do
      [] -> tokens
      kept -> kept
    end
  end

  @doc "Remove diacritics, returning ASCII-folded text."
  @spec deaccent(binary()) :: binary()
  def deaccent(str) do
    str
    |> :unicode.characters_to_nfd_binary()
    |> String.replace(~r/[\x{0300}-\x{036f}]/u, "")
  end
end
