defmodule Soccer.Names do
  @moduledoc false

  @clubs [
    {"América-MG", ["america fc minas gerais", "america mg"]},
    {"América-RN", ["america rn"]},
    {"Atlético-GO", ["atletico goianiense", "atletico go"]},
    {"Atlético-MG", ["atletico mineiro", "clube atletico mineiro", "atletico mg"]},
    {"Athletico-PR",
     [
       "atletico pr",
       "athletico pr",
       "athletico",
       "atletico paranaense",
       "athletico paranaense",
       "club athletico paranaense"
     ]},
    {"Botafogo", ["botafogo fr", "botafogo de futebol e regatas"]},
    {"Botafogo-SP", ["botafogo sp", "botafogo ribeirao preto"]},
    {"Botafogo-PB", ["botafogo pb"]},
    {"Bahia", ["ec bahia", "esporte clube bahia"]},
    {"Ceará", ["ceara sc", "ceara sporting club"]},
    {"Corinthians",
     ["sport club corinthians paulista", "corinthians paulista", "sc corinthians paulista"]},
    {"Flamengo", ["clube de regatas do flamengo", "cr flamengo"]},
    {"Fluminense", ["fluminense football club", "fluminense fc"]},
    {"Fortaleza", ["fortaleza fc", "fortaleza ec", "fortaleza esporte clube"]},
    {"Grêmio", ["gremio fbpa", "gremio foot ball porto alegrense"]},
    {"Internacional",
     ["sc internacional", "sport club internacional", "internacional porto alegre"]},
    {"Juventude", ["ec juventude", "esporte clube juventude"]},
    {"Palmeiras", ["sociedade esportiva palmeiras", "se palmeiras"]},
    {"Red Bull Bragantino", ["bragantino", "rb bragantino"]},
    {"Santa Cruz", ["santa cruz fc", "santa cruz futebol clube"]},
    {"Santos", ["santos fc", "santos futebol clube"]},
    {"São Paulo", ["sao paulo fc", "sao paulo futebol clube"]},
    {"Sport", ["sport recife", "sport club do recife", "sport club recife"]},
    {"Vasco da Gama", ["vasco", "cr vasco da gama", "club de regatas vasco da gama"]},
    {"Vitória", ["ec vitoria", "vitoria ec", "esporte clube vitoria"]},
    {"Avaí", []},
    {"Goiás", []},
    {"Criciúma", []},
    {"Cuiabá", []},
    {"Náutico", ["nautico capibaribe"]},
    {"Paraná", ["parana clube"]},
    {"CSA", []},
    {"CRB", []},
    {"ABC", []},
    {"4 de Julho", ["4 de julho ec"]},
    {"Afogados", ["afogados da ingazeira fc"]},
    {"Aimoré", ["ce aimore"]},
    {"Altos", ["ae altos"]},
    {"Anápolis", ["anapolis fc"]},
    {"Atlético-AC", ["atletico acreano"]},
    {"Atlético Cearense", ["fc atletico cearense"]},
    {"Boavista", ["boavista sc saquarema", "boavista sport club antigo esporte clube barreira"]},
    {"Bragantino-PA", []},
    {"Brasil de Pelotas", ["brasil rs"]},
    {"Brasília", ["brasilia fc"]},
    {"Campinense", ["campinense clube"]},
    {"Dom Bosco", ["ce dom bosco"]},
    {"Gama", ["se gama"]},
    {"Genus", ["sc genus"]},
    {"Globo", ["globo fc"]},
    {"Guarany de Sobral", ["guarany ce"]},
    {"Internacional-SC", ["ec internacional sc"]},
    {"Jaraguá", ["jaragua ec"]},
    {"Maringá", ["metropolitano maringa pr"]},
    {"Moto Club", ["moto club de sao luis", "moto clube"]},
    {"Nacional-AM", []},
    {"Nacional-URU", []},
    {"Nacional-PAR", []},
    {"Náutico-RR", []},
    {"Novorizontino", ["gremio novorizontino"]},
    {"Operário-MT", []},
    {"Operário-PR", ["operario ferroviario", "operario fc"]},
    {"Palmas", ["palmas fr"]},
    {"Portuguesa", ["portuguesa desportos"]},
    {"Remo", ["clube do remo"]},
    {"Retrô", ["retro fc brasil"]},
    {"Rio Branco-AC", []},
    {"Rio Branco-ES", []},
    {"Ríver", ["river pi"]},
    {"Santa Cruz-RN", []},
    {"Santos-AP", []},
    {"São Raimundo-PA", []},
    {"São Raimundo-RR", []},
    {"Serra", ["serra f c"]},
    {"Sete de Setembro", ["7 de setembro"]},
    {"Sinop", ["sinop fc"]},
    {"Toledo", ["toledo ec"]},
    {"Votuporanguense", ["ca votuporanguense"]},
    {"Vitória-ES", ["vitoria f c es"]},
    {"Ypiranga", ["ypiranga rs"]},
    {"Ypiranga-AP", []},
    {"Delfín", ["delfin equ"]},
    {"Guaraní-PAR", []},
    {"Libertad", ["libertad par"]},
    {"Universitario-PER", []}
  ]

  def fold(text) do
    text
    |> String.normalize(:nfd)
    |> String.replace(~r/\p{M}/u, "")
    |> String.downcase()
    |> String.replace(~r/[^a-z0-9]+/u, " ")
    |> String.trim()
  end

  @aliases (for {name, aliases} <- @clubs, alias_name <- [name | aliases], into: %{} do
              key =
                name
                |> String.normalize(:nfd)
                |> String.replace(~r/\p{M}/u, "")
                |> String.downcase()
                |> String.replace(~r/[^a-z0-9]+/u, " ")

              {if(alias_name == name, do: key, else: alias_name), {key, name}}
            end)

  def club(name) do
    key = fold(name)

    state =
      ~r/\s+(?:ac|al|ap|am|ba|ce|df|es|go|ma|mt|ms|mg|pa|pb|pr|pe|pi|rj|rn|rs|ro|rr|sc|sp|se|to)$/

    base = String.replace(key, state, "")

    Map.get(@aliases, key) || Map.get(@aliases, base) ||
      {base,
       if(base == key,
         do: String.trim(name),
         else: String.replace(String.trim(name), ~r/(?:\s*-\s*|\s+)[A-Za-z]{2}$/, "")
       )}
  end

  def competition(name) do
    case fold(name) do
      name
      when name in ["brasileirao", "brasileirao serie a", "serie a", "campeonato brasileiro"] ->
        "Brasileirão Série A"

      name when name in ["brasileirao serie b", "serie b"] ->
        "Brasileirão Série B"

      name when name in ["brasileirao serie c", "serie c"] ->
        "Brasileirão Série C"

      name when name in ["copa do brasil", "brazilian cup"] ->
        "Copa do Brasil"

      name when name in ["libertadores", "copa libertadores", "conmebol libertadores"] ->
        "Copa Libertadores"

      _ ->
        name
    end
  end
end
