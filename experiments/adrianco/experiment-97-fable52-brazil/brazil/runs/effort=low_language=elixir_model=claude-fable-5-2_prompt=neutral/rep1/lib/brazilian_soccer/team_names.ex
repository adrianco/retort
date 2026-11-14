defmodule BrazilianSoccer.TeamNames do
  @moduledoc """
  Team-name normalisation.

  The datasets spell the same club in many ways ("Palmeiras-SP", "Palmeiras",
  "Grêmio" / "Gremio", "EC Bahia", "Vasco Da Gama RJ", "Sport Club do Recife",
  "Athletico-PR" / "Atlético Paranaense" ...). `parse/1` reduces a raw name to
  an accent-free *base* plus an optional state/country code. Deciding whether
  two bases with different states are different clubs ("Flamengo-RJ" vs
  "Flamengo-PI") is done by `BrazilianSoccer.Data` using every name it sees.
  """

  alias BrazilianSoccer.Text

  @ufs ~w(AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO)
  # "SC" after a space usually means "Sport Club", not Santa Catarina.
  @space_ufs @ufs -- ["SC"]

  # normalised name => {base, state | nil}
  @aliases %{
    "vasco da gama" => {"vasco", "RJ"},
    "sport recife" => {"sport", "PE"},
    "sport club do recife" => {"sport", "PE"},
    "nautico capibaribe" => {"nautico", "PE"},
    "atletico mineiro" => {"atletico", "MG"},
    "clube atletico mineiro" => {"atletico", "MG"},
    "atletico paranaense" => {"atletico", "PR"},
    "athletico paranaense" => {"atletico", "PR"},
    "club athletico paranaense" => {"atletico", "PR"},
    "athletico" => {"atletico", "PR"},
    "atletico goianiense" => {"atletico", "GO"},
    "red bull bragantino" => {"bragantino", "SP"},
    "rb bragantino" => {"bragantino", "SP"},
    "america mineiro" => {"america", "MG"},
    "america fc minas gerais" => {"america", "MG"},
    "ceara sporting club" => {"ceara", nil},
    "clube do remo" => {"remo", nil},
    "brasil de pelotas" => {"brasil", "RS"},
    "portuguesa desportos" => {"portuguesa", "SP"},
    "gremio novorizontino" => {"novorizontino", nil},
    "gremio barueri" => {"barueri", nil},
    "flamengo do piaui" => {"flamengo", "PI"},
    "corinthians paulista" => {"corinthians", nil},
    "sport club corinthians paulista" => {"corinthians", nil},
    "sociedade esportiva palmeiras" => {"palmeiras", nil},
    "clube de regatas do flamengo" => {"flamengo", "RJ"},
    "fortaleza esporte clube" => {"fortaleza", nil},
    "gremio foot-ball porto alegrense" => {"gremio", nil},
    "sport club internacional" => {"internacional", "RS"},
    "botafogo de futebol e regatas" => {"botafogo", "RJ"},
    "fluminense football club" => {"fluminense", "RJ"},
    "cruzeiro esporte clube" => {"cruzeiro", nil},
    "esporte clube bahia" => {"bahia", nil},
    "santos futebol clube" => {"santos", nil},
    "sao paulo futebol clube" => {"sao paulo", nil},
    "ldu quito" => {"ldu", nil}
  }

  @prefixes ~w(ec fc sc ad ae se cs)
  @suffixes ["futebol clube", "esporte clube", "sport club", "fc", "ec", "sc", "ltda"]

  @doc """
  Parses a raw team name into `{base, state, label}` where `base` is the
  normalised club name, `state` an upper-case state/country code or nil and
  `label` the raw name without its state suffix.
  """
  def parse(raw) when is_binary(raw) do
    s = String.trim(raw)

    {s, state} =
      case Regex.run(~r/^(.*?)\s*\(([A-Z]{2,3})\)\s*$/u, s) do
        [_, rest, code] -> {rest, code}
        _ -> {s, nil}
      end

    alias_hit = Map.get(@aliases, s |> String.replace(~r/[()]/, "") |> clean())
    s = s |> String.replace(~r/\s*\([^)]*\)/u, "") |> String.trim()

    {s, state} =
      cond do
        state != nil ->
          {s, state}

        m = Regex.run(~r/^(.*?\S)\s*-\s*([A-Za-z]{2,3})$/u, s) ->
          [_, rest, code] = m
          up = String.upcase(code)
          # lower-case suffixes are only accepted for real state codes
          if code == up or up in @ufs, do: {rest, up}, else: {s, nil}

        m = Regex.run(~r/^(.*\S)\s+([A-Z]{2})$/u, s) ->
          [_, rest, code] = m
          if code in @space_ufs, do: {rest, code}, else: {s, nil}

        true ->
          {s, nil}
      end

    label = String.trim(s)
    base = clean(label)

    {base, alias_state} =
      case alias_hit || Map.get(@aliases, base) do
        nil ->
          stripped = strip_affixes(base)
          Map.get(@aliases, stripped, {stripped, nil})

        hit ->
          hit
      end

    {base, state || alias_state, label}
  end

  @doc "True when the full name is a known alias of a club."
  def alias?(raw), do: Map.has_key?(@aliases, raw |> String.replace(~r/[()]/, "") |> clean())

  @doc "Lower-case, accent-free, punctuation-free form used for comparisons."
  def clean(s) do
    s =
      s
      |> Text.normalize()
      |> String.replace(~r/[.'’]/u, " ")
      |> String.replace(~r/\s+/, " ")
      |> String.trim()

    tokens = String.split(s, " ", trim: true)

    # "C. R. B." / "A.b.c." => "crb" / "abc"
    if length(tokens) > 1 and Enum.all?(tokens, &(String.length(&1) == 1)) do
      Enum.join(tokens)
    else
      s
    end
  end

  defp strip_affixes(base) do
    tokens = String.split(base, " ", trim: true)

    tokens =
      case tokens do
        [p | [_ | _] = rest] when p in @prefixes -> rest
        _ -> tokens
      end

    base = Enum.join(tokens, " ")

    Enum.reduce_while(@suffixes, base, fn suf, acc ->
      if String.ends_with?(acc, " " <> suf) do
        {:halt, acc |> String.replace_suffix(" " <> suf, "") |> String.trim()}
      else
        {:cont, acc}
      end
    end)
  end

  @doc "Traditional rivalries (derbies) as `{team_a, team_b, nickname}`."
  def derbies do
    [
      {"Flamengo", "Fluminense", "Fla-Flu"},
      {"Flamengo", "Vasco", "Clássico dos Milhões"},
      {"Flamengo", "Botafogo-RJ", "Clássico da Rivalidade"},
      {"Fluminense", "Vasco", "Clássico dos Gigantes"},
      {"Botafogo-RJ", "Fluminense", "Clássico Vovô"},
      {"Botafogo-RJ", "Vasco", "Clássico da Amizade"},
      {"Corinthians", "Palmeiras", "Derby Paulista"},
      {"Corinthians", "São Paulo", "Majestoso"},
      {"Palmeiras", "São Paulo", "Choque-Rei"},
      {"Corinthians", "Santos", "Clássico Alvinegro"},
      {"Palmeiras", "Santos", "Clássico da Saudade"},
      {"Santos", "São Paulo", "San-São"},
      {"Grêmio", "Internacional", "Grenal"},
      {"Atlético-MG", "Cruzeiro", "Clássico Mineiro"},
      {"Bahia", "Vitória", "Ba-Vi"},
      {"Athletico-PR", "Coritiba", "Atletiba"},
      {"Ceará", "Fortaleza", "Clássico-Rei"},
      {"Sport", "Náutico", "Clássico dos Clássicos"},
      {"Sport", "Santa Cruz", "Clássico das Multidões"},
      {"Náutico", "Santa Cruz", "Clássico das Emoções"},
      {"Goiás", "Vila Nova", "Derby do Cerrado"},
      {"Avaí", "Figueirense", "Clássico de Florianópolis"},
      {"Remo", "Paysandu", "Re-Pa"}
    ]
  end
end
