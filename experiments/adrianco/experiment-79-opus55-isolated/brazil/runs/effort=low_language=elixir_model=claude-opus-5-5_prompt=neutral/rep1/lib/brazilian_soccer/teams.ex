defmodule BrazilianSoccer.Teams do
  @moduledoc """
  Team name normalisation.

  The datasets spell the same club many ways ("Palmeiras-SP", "Palmeiras",
  "Atlético - MG", "Atletico Mineiro", "Vasco da Gama - RJ", "Vasco"). Every
  name is resolved to a `key` (accent-free canonical identifier), an optional
  `state` (Brazilian UF or a 3-letter country code) and a display `name`.

  The state matters because several distinct clubs share a base name
  (Atlético MG/PR/GO, Botafogo RJ/SP/PB, Flamengo RJ/PI, ...). Two references
  denote the same club when their keys are equal and their states are equal
  or one of them is unknown.
  """

  alias BrazilianSoccer.Text

  @ufs ~w(AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO)

  # key => {default state, display name}
  @clubs %{
    "flamengo" => {"RJ", "Flamengo"},
    "fluminense" => {"RJ", "Fluminense"},
    "vasco" => {"RJ", "Vasco da Gama"},
    "botafogo" => {"RJ", "Botafogo"},
    "corinthians" => {"SP", "Corinthians"},
    "palmeiras" => {"SP", "Palmeiras"},
    "sao paulo" => {"SP", "São Paulo"},
    "santos" => {"SP", "Santos"},
    "gremio" => {"RS", "Grêmio"},
    "internacional" => {"RS", "Internacional"},
    "cruzeiro" => {"MG", "Cruzeiro"},
    "atletico mineiro" => {"MG", "Atlético Mineiro"},
    "america mineiro" => {"MG", "América Mineiro"},
    "athletico paranaense" => {"PR", "Athletico Paranaense"},
    "coritiba" => {"PR", "Coritiba"},
    "parana" => {"PR", "Paraná"},
    "bahia" => {"BA", "Bahia"},
    "vitoria" => {"BA", "Vitória"},
    "sport" => {"PE", "Sport Recife"},
    "nautico" => {"PE", "Náutico"},
    "santa cruz" => {"PE", "Santa Cruz"},
    "fortaleza" => {"CE", "Fortaleza"},
    "ceara" => {"CE", "Ceará"},
    "goias" => {"GO", "Goiás"},
    "atletico goianiense" => {"GO", "Atlético Goianiense"},
    "vila nova" => {"GO", "Vila Nova"},
    "chapecoense" => {"SC", "Chapecoense"},
    "figueirense" => {"SC", "Figueirense"},
    "avai" => {"SC", "Avaí"},
    "criciuma" => {"SC", "Criciúma"},
    "joinville" => {"SC", "Joinville"},
    "ponte preta" => {"SP", "Ponte Preta"},
    "guarani" => {"SP", "Guarani"},
    "portuguesa" => {"SP", "Portuguesa"},
    "bragantino" => {"SP", "Red Bull Bragantino"},
    "sao caetano" => {"SP", "São Caetano"},
    "santo andre" => {"SP", "Santo André"},
    "barueri" => {"SP", "Grêmio Barueri"},
    "juventude" => {"RS", "Juventude"},
    "cuiaba" => {"MT", "Cuiabá"},
    "csa" => {"AL", "CSA"},
    "crb" => {"AL", "CRB"},
    "paysandu" => {"PA", "Paysandu"},
    "remo" => {"PA", "Remo"},
    "ipatinga" => {"MG", "Ipatinga"},
    "brasiliense" => {"DF", "Brasiliense"},
    "abc" => {"RN", "ABC"},
    "america natal" => {"RN", "América-RN"}
  }

  # normalised base name => key
  @aliases %{
    "vasco da gama" => "vasco",
    "cr vasco da gama" => "vasco",
    "sport recife" => "sport",
    "sport club do recife" => "sport",
    "sport club corinthians paulista" => "corinthians",
    "corinthians paulista" => "corinthians",
    "sociedade esportiva palmeiras" => "palmeiras",
    "clube de regatas do flamengo" => "flamengo",
    "mengo" => "flamengo",
    "sao paulo futebol clube" => "sao paulo",
    "spfc" => "sao paulo",
    "sport club internacional" => "internacional",
    "gremio foot ball porto alegrense" => "gremio",
    "atletico mineiro" => "atletico mineiro",
    "clube atletico mineiro" => "atletico mineiro",
    "galo" => "atletico mineiro",
    "atletico paranaense" => "athletico paranaense",
    "athletico" => "athletico paranaense",
    "athletico pr" => "athletico paranaense",
    "club athletico paranaense" => "athletico paranaense",
    "atletico go" => "atletico goianiense",
    "atletico mg" => "atletico mineiro",
    "atletico pr" => "athletico paranaense",
    "atletico acreano" => "atletico acreano",
    "america mg" => "america mineiro",
    "america minas gerais" => "america mineiro",
    "america fc minas gerais" => "america mineiro",
    "america rn" => "america natal",
    "america fc natal" => "america natal",
    "america natal" => "america natal",
    "red bull bragantino" => "bragantino",
    "rb bragantino" => "bragantino",
    "cs alagoano" => "csa",
    "c s a" => "csa",
    "c r b" => "crb",
    "a b c" => "abc",
    "a s a" => "asa",
    "nautico capibaribe" => "nautico",
    "clube do remo" => "remo",
    "ceara sporting club" => "ceara",
    "portuguesa desportos" => "portuguesa",
    "gremio barueri" => "barueri",
    "brasil de pelotas" => "brasil",
    "fortaleza esporte clube" => "fortaleza",
    "esporte clube bahia" => "bahia",
    "esporte clube vitoria" => "vitoria",
    "goias esporte clube" => "goias",
    "santos futebol clube" => "santos",
    "fluminense football club" => "fluminense",
    "botafogo de futebol e regatas" => "botafogo",
    "cruzeiro esporte clube" => "cruzeiro",
    "coritiba foot ball club" => "coritiba"
  }

  # {base name, state} => key, for names that are only unique with a state
  @state_aliases %{
    {"atletico", "MG"} => "atletico mineiro",
    {"atletico", "PR"} => "athletico paranaense",
    {"athletico", "PR"} => "athletico paranaense",
    {"atletico", "GO"} => "atletico goianiense",
    {"atletico", "AC"} => "atletico acreano",
    {"america", "MG"} => "america mineiro",
    {"america", "RN"} => "america natal",
    {"brasil", "RS"} => "brasil"
  }

  @affixes ~w(fc ec sc ad ae ca se cr)

  # Traditional rivalries (pairs of keys) used by the derby queries.
  @derbies [
    {"flamengo", "fluminense", "Fla-Flu"},
    {"flamengo", "vasco", "Clássico dos Milhões"},
    {"flamengo", "botafogo", "Clássico da Rivalidade"},
    {"fluminense", "vasco", "Clássico dos Gigantes"},
    {"fluminense", "botafogo", "Clássico Vovô"},
    {"botafogo", "vasco", "Clássico da Amizade"},
    {"corinthians", "palmeiras", "Derby Paulista"},
    {"corinthians", "sao paulo", "Majestoso"},
    {"corinthians", "santos", "Clássico Alvinegro"},
    {"palmeiras", "sao paulo", "Choque-Rei"},
    {"palmeiras", "santos", "Clássico da Saudade"},
    {"santos", "sao paulo", "San-São"},
    {"gremio", "internacional", "Gre-Nal"},
    {"atletico mineiro", "cruzeiro", "Clássico Mineiro"},
    {"athletico paranaense", "coritiba", "Atletiba"},
    {"bahia", "vitoria", "Ba-Vi"},
    {"ceara", "fortaleza", "Clássico-Rei"},
    {"sport", "nautico", "Clássico dos Clássicos"},
    {"sport", "santa cruz", "Clássico das Multidões"},
    {"nautico", "santa cruz", "Clássico das Emoções"},
    {"goias", "vila nova", "Derby do Cerrado"},
    {"avai", "figueirense", "Clássico de Florianópolis"},
    {"remo", "paysandu", "Re-Pa"},
    {"guarani", "ponte preta", "Derby Campineiro"},
    {"crb", "csa", "Clássico das Multidões (AL)"}
  ]

  def derbies, do: @derbies

  @doc "True when the key belongs to one of the well-known Brazilian clubs."
  def brazilian_club?(key), do: Map.has_key?(@clubs, key)

  @doc "Returns the derby nickname when the two keys are traditional rivals."
  def derby_name(key_a, key_b) do
    Enum.find_value(@derbies, fn {a, b, name} ->
      if (a == key_a and b == key_b) or (a == key_b and b == key_a), do: name
    end)
  end

  @doc """
  Resolves a raw team name into `%{key: _, state: _, name: _}`.

  `uf` may be given when the dataset carries the state in a separate column.
  """
  def resolve(raw, uf \\ nil) when is_binary(raw) do
    {base, suffix_state} = split_state(String.trim(raw))
    state = normalize_state(uf) || suffix_state
    norm = normalize_base(base)

    key =
      Map.get(@state_aliases, {norm, state}) ||
        Map.get(@aliases, norm) ||
        strip_affixes(norm)

    key = Map.get(@aliases, key, key)

    case Map.get(@clubs, key) do
      {default, display} when state in [nil, default] ->
        %{key: key, state: default, name: display}

      _ ->
        name = String.trim(base)
        %{key: key, state: state, name: if(state, do: "#{name}-#{state}", else: name)}
    end
  end

  @doc "True when a resolved reference matches a (key, state) pair."
  def same?(%{key: k1, state: s1}, k2, s2), do: k1 == k2 and (s1 == nil or s2 == nil or s1 == s2)

  defp normalize_state(nil), do: nil

  defp normalize_state(s) do
    s = s |> String.trim() |> String.upcase()
    if s in @ufs, do: s, else: nil
  end

  # "Palmeiras-SP", "América - MG", "Barcelona-EQU"
  # "Nacional (URU)"
  # "Botafogo RJ"
  defp split_state(s) do
    cond do
      m = Regex.run(~r/^(.+?)\s*-\s*([A-Za-z]{2})$/u, s) ->
        [_, base, st] = m
        st = String.upcase(st)
        if st in @ufs, do: {base, st}, else: {s, nil}

      m = Regex.run(~r/^(.+?)\s*-\s*([A-Z]{3})$/u, s) ->
        [_, base, st] = m
        {base, st}

      m = Regex.run(~r/^(.+?)\s*\(([A-Z]{2,3})\)$/u, s) ->
        [_, base, st] = m
        {base, st}

      m = Regex.run(~r/^(.+)\s([A-Z]{2})$/u, s) ->
        [_, base, st] = m
        if st in @ufs, do: {base, st}, else: {s, nil}

      true ->
        {s, nil}
    end
  end

  defp normalize_base(base) do
    base
    |> Text.fold()
    |> String.replace(".", "")
    |> String.replace(~r/[^a-z0-9]+/, " ")
    |> String.trim()
  end

  defp strip_affixes(norm) do
    tokens = String.split(norm, " ", trim: true)
    tokens = if length(tokens) > 1 and hd(tokens) in @affixes, do: tl(tokens), else: tokens

    tokens =
      if length(tokens) > 1 and List.last(tokens) in @affixes,
        do: Enum.drop(tokens, -1),
        else: tokens

    Enum.join(tokens, " ")
  end
end
