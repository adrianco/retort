// aliases.go is the curated knowledge that the raw CSVs do not contain:
// which spellings refer to the same club, what the competitions are called and
// which fixtures are traditional derbies.
//
// Anything not listed here still resolves through the generic rules in
// normalize.go + registry.go (noise stripping plus state inference), so the
// table only needs to cover clubs whose spellings genuinely differ between
// datasets ("Atletico Paranaense" / "Athletico-PR" / "Athletico") or whose
// bare name is ambiguous ("Botafogo", "River Plate").
package soccer

import "strings"

// CanonTeam is a curated club identity.
//
// Aliases are written the way they appear in the sources; they are normalised
// at start-up. An alias that carries no state/country qualifier also claims the
// bare name, which is how "Botafogo" becomes Botafogo-RJ rather than staying
// ambiguous with Botafogo-PB and Botafogo-SP.
type CanonTeam struct {
	ID      string
	Name    string
	State   string
	Country string
	Aliases []string
}

var canonicalTeams = []CanonTeam{
	// ---- Rio de Janeiro -----------------------------------------------------
	{ID: "flamengo-rj", Name: "Flamengo", State: "RJ", Country: "BRA",
		Aliases: []string{"Flamengo", "Flamengo-RJ", "CR Flamengo", "Clube de Regatas do Flamengo"}},
	{ID: "fluminense-rj", Name: "Fluminense", State: "RJ", Country: "BRA",
		Aliases: []string{"Fluminense", "Fluminense-RJ", "Fluminense FC"}},
	{ID: "botafogo-rj", Name: "Botafogo", State: "RJ", Country: "BRA",
		Aliases: []string{"Botafogo", "Botafogo-RJ", "Botafogo RJ", "Botafogo de Futebol e Regatas"}},
	{ID: "vasco-rj", Name: "Vasco da Gama", State: "RJ", Country: "BRA",
		Aliases: []string{"Vasco", "Vasco da Gama", "Vasco Da Gama RJ", "Vasco da Gama-RJ", "CR Vasco da Gama"}},
	{ID: "americano-rj", Name: "Americano", State: "RJ", Country: "BRA",
		Aliases: []string{"Americano", "Americano - RJ", "Americano RJ"}},
	{ID: "macae-rj", Name: "Macaé", State: "RJ", Country: "BRA",
		Aliases: []string{"Macae", "Macae Esporte FC", "Macae Esporte RJ", "Macaé Esporte - RJ"}},
	{ID: "boavista-rj", Name: "Boavista", State: "RJ", Country: "BRA",
		Aliases: []string{"Boavista", "Boavista Sport Club - RJ"}},

	// ---- São Paulo ----------------------------------------------------------
	{ID: "palmeiras-sp", Name: "Palmeiras", State: "SP", Country: "BRA",
		Aliases: []string{"Palmeiras", "Palmeiras-SP", "SE Palmeiras", "Sociedade Esportiva Palmeiras"}},
	{ID: "corinthians-sp", Name: "Corinthians", State: "SP", Country: "BRA",
		Aliases: []string{"Corinthians", "Corinthians-SP", "Corinthians Paulista", "Sport Club Corinthians Paulista"}},
	{ID: "sao-paulo-sp", Name: "São Paulo", State: "SP", Country: "BRA",
		Aliases: []string{"Sao Paulo", "São Paulo", "Sao Paulo-SP", "São Paulo FC", "Sao Paulo FC"}},
	{ID: "santos-sp", Name: "Santos", State: "SP", Country: "BRA",
		Aliases: []string{"Santos", "Santos-SP", "Santos FC"}},
	{ID: "ponte-preta-sp", Name: "Ponte Preta", State: "SP", Country: "BRA",
		Aliases: []string{"Ponte Preta", "Ponte Preta-SP", "AA Ponte Preta"}},
	{ID: "portuguesa-sp", Name: "Portuguesa", State: "SP", Country: "BRA",
		Aliases: []string{"Portuguesa", "Portuguesa-SP", "Portuguesa Desportos", "AA Portuguesa"}},
	{ID: "guarani-sp", Name: "Guarani", State: "SP", Country: "BRA",
		Aliases: []string{"Guarani", "Guarani-SP", "Guarani SP", "Guarani FC"}},
	{ID: "bragantino-sp", Name: "Red Bull Bragantino", State: "SP", Country: "BRA",
		Aliases: []string{"Bragantino", "Bragantino-SP", "Red Bull Bragantino", "Red Bull Bragantino-SP", "RB Bragantino"}},
	{ID: "sao-caetano-sp", Name: "São Caetano", State: "SP", Country: "BRA",
		Aliases: []string{"Sao Caetano", "São Caetano", "AD São Caetano"}},
	{ID: "santo-andre-sp", Name: "Santo André", State: "SP", Country: "BRA",
		Aliases: []string{"Santo Andre", "Santo André", "EC Santo André"}},
	{ID: "sao-bento-sp", Name: "São Bento", State: "SP", Country: "BRA",
		Aliases: []string{"Sao Bento", "São Bento", "EC São Bento"}},
	{ID: "novorizontino-sp", Name: "Novorizontino", State: "SP", Country: "BRA",
		Aliases: []string{"Novorizontino", "Gremio Novorizontino", "Grêmio Novorizontino"}},
	{ID: "oeste-sp", Name: "Oeste", State: "SP", Country: "BRA", Aliases: []string{"Oeste", "Oeste FC"}},
	{ID: "ituano-sp", Name: "Ituano", State: "SP", Country: "BRA", Aliases: []string{"Ituano", "Ituano FC"}},
	{ID: "mirassol-sp", Name: "Mirassol", State: "SP", Country: "BRA", Aliases: []string{"Mirassol", "Mirassol FC"}},
	{ID: "mogi-mirim-sp", Name: "Mogi Mirim", State: "SP", Country: "BRA", Aliases: []string{"Mogi Mirim", "Mogi Mirim EC"}},
	{ID: "barueri-sp", Name: "Grêmio Barueri", State: "SP", Country: "BRA",
		Aliases: []string{"Barueri", "Gremio Barueri", "Grêmio Barueri"}},
	{ID: "gremio-prudente-sp", Name: "Grêmio Prudente", State: "SP", Country: "BRA",
		Aliases: []string{"Gremio Prudente", "Grêmio Prudente"}},

	// ---- Rio Grande do Sul --------------------------------------------------
	{ID: "gremio-rs", Name: "Grêmio", State: "RS", Country: "BRA",
		Aliases: []string{"Gremio", "Grêmio", "Gremio-RS", "Grêmio FBPA", "Gremio Foot-Ball Porto Alegrense"}},
	{ID: "internacional-rs", Name: "Internacional", State: "RS", Country: "BRA",
		Aliases: []string{"Internacional", "Internacional-RS", "SC Internacional"}},
	{ID: "juventude-rs", Name: "Juventude", State: "RS", Country: "BRA",
		Aliases: []string{"Juventude", "Juventude-RS", "EC Juventude"}},
	{ID: "brasil-de-pelotas-rs", Name: "Brasil de Pelotas", State: "RS", Country: "BRA",
		Aliases: []string{"Brasil de Pelotas", "GE Brasil", "Brasil-RS"}},
	{ID: "bage-rs", Name: "Bagé", State: "RS", Country: "BRA", Aliases: []string{"GE Bage", "Bage", "Bagé"}},

	// ---- Minas Gerais -------------------------------------------------------
	{ID: "atletico-mg", Name: "Atlético-MG", State: "MG", Country: "BRA",
		Aliases: []string{"Atletico-MG", "Atlético-MG", "Atletico MG", "Atletico Mineiro", "Atlético Mineiro", "Clube Atlético Mineiro", "Galo"}},
	{ID: "cruzeiro-mg", Name: "Cruzeiro", State: "MG", Country: "BRA",
		Aliases: []string{"Cruzeiro", "Cruzeiro-MG", "Cruzeiro EC"}},
	{ID: "america-mg", Name: "América-MG", State: "MG", Country: "BRA",
		Aliases: []string{"America-MG", "América-MG", "America MG", "América - MG", "America Mineiro", "América Mineiro", "América FC (Minas Gerais)"}},
	{ID: "tombense-mg", Name: "Tombense", State: "MG", Country: "BRA",
		Aliases: []string{"Tombense", "Tombense MG", "Tombense-MG"}},
	{ID: "villa-nova-mg", Name: "Villa Nova", State: "MG", Country: "BRA",
		Aliases: []string{"Villa Nova", "Villa Nova AC"}},
	{ID: "ipatinga-mg", Name: "Ipatinga", State: "MG", Country: "BRA", Aliases: []string{"Ipatinga"}},
	{ID: "tupi-mg", Name: "Tupi", State: "MG", Country: "BRA", Aliases: []string{"Tupi", "Tupi MG", "Tupi-MG"}},
	{ID: "athletic-mg", Name: "Athletic Club", State: "MG", Country: "BRA",
		Aliases: []string{"Athletic Club MG", "Athletic-MG"}},
	{ID: "caldense-mg", Name: "Caldense", State: "MG", Country: "BRA", Aliases: []string{"Caldense"}},

	// ---- Paraná -------------------------------------------------------------
	{ID: "athletico-pr", Name: "Athletico-PR", State: "PR", Country: "BRA",
		Aliases: []string{"Athletico", "Athletico-PR", "Atletico-PR", "Atlético-PR", "Athletico PR",
			"Atletico Paranaense", "Athletico Paranaense", "Atlético Paranaense", "Clube Atlético Paranaense"}},
	{ID: "coritiba-pr", Name: "Coritiba", State: "PR", Country: "BRA",
		Aliases: []string{"Coritiba", "Coritiba-PR", "Coritiba FBC"}},
	{ID: "parana-pr", Name: "Paraná", State: "PR", Country: "BRA",
		Aliases: []string{"Parana", "Paraná", "Parana-PR", "CA Parana", "Paraná Clube"}},
	{ID: "londrina-pr", Name: "Londrina", State: "PR", Country: "BRA", Aliases: []string{"Londrina", "Londrina EC"}},
	{ID: "operario-pr", Name: "Operário", State: "PR", Country: "BRA",
		Aliases: []string{"Operario PR", "Operário - PR", "Operario Ferroviario", "Operário Ferroviário"}},
	{ID: "arapongas-pr", Name: "Arapongas", State: "PR", Country: "BRA",
		Aliases: []string{"Arapongas", "Arapongas Esporte Clube - PR"}},

	// ---- Goiás / Centro-Oeste ----------------------------------------------
	{ID: "atletico-go", Name: "Atlético-GO", State: "GO", Country: "BRA",
		Aliases: []string{"Atletico-GO", "Atlético-GO", "Atletico GO", "Atletico Goianiense", "Atlético Goianiense"}},
	{ID: "goias-go", Name: "Goiás", State: "GO", Country: "BRA",
		Aliases: []string{"Goias", "Goiás", "Goias-GO", "Goiás EC"}},
	{ID: "vila-nova-go", Name: "Vila Nova", State: "GO", Country: "BRA",
		Aliases: []string{"Vila Nova", "Vila Nova FC", "Vila Nova - GO"}},
	{ID: "aparecidense-go", Name: "Aparecidense", State: "GO", Country: "BRA",
		Aliases: []string{"Aparecidense", "Aparecidense GO", "Aparecidense - GO"}},
	{ID: "anapolis-go", Name: "Anápolis", State: "GO", Country: "BRA",
		Aliases: []string{"Anapolis", "Anápolis", "Anapolis FC"}},
	{ID: "brasiliense-df", Name: "Brasiliense", State: "DF", Country: "BRA",
		Aliases: []string{"Brasiliense", "Brasiliense FC"}},
	{ID: "gama-df", Name: "Gama", State: "DF", Country: "BRA", Aliases: []string{"Gama", "SE Gama"}},
	{ID: "cuiaba-mt", Name: "Cuiabá", State: "MT", Country: "BRA",
		Aliases: []string{"Cuiaba", "Cuiabá", "Cuiaba-MT", "Cuiabá EC"}},
	{ID: "luverdense-mt", Name: "Luverdense", State: "MT", Country: "BRA", Aliases: []string{"Luverdense"}},

	// ---- Bahia / Nordeste ---------------------------------------------------
	{ID: "bahia-ba", Name: "Bahia", State: "BA", Country: "BRA",
		Aliases: []string{"Bahia", "Bahia-BA", "EC Bahia", "Esporte Clube Bahia"}},
	{ID: "vitoria-ba", Name: "Vitória", State: "BA", Country: "BRA",
		Aliases: []string{"Vitoria", "Vitória", "Vitoria-BA", "EC Vitoria", "EC Vitória"}},
	{ID: "sport-pe", Name: "Sport Recife", State: "PE", Country: "BRA",
		Aliases: []string{"Sport", "Sport-PE", "Sport Recife", "Sport Club do Recife", "Sport Club Recife"}},
	{ID: "nautico-pe", Name: "Náutico", State: "PE", Country: "BRA",
		Aliases: []string{"Nautico", "Náutico", "Nautico-PE", "Nautico Capibaribe", "Clube Náutico Capibaribe"}},
	{ID: "santa-cruz-pe", Name: "Santa Cruz", State: "PE", Country: "BRA",
		Aliases: []string{"Santa Cruz", "Santa Cruz-PE", "Santa Cruz FC"}},
	{ID: "ceara-ce", Name: "Ceará", State: "CE", Country: "BRA",
		Aliases: []string{"Ceara", "Ceará", "Ceara-CE", "Ceara SC", "Ceará Sporting Club"}},
	{ID: "fortaleza-ce", Name: "Fortaleza", State: "CE", Country: "BRA",
		Aliases: []string{"Fortaleza", "Fortaleza-CE", "Fortaleza EC", "Fortaleza FC", "Fortaleza Esporte Clube"}},
	{ID: "icasa-ce", Name: "Icasa", State: "CE", Country: "BRA", Aliases: []string{"Icasa", "AD Icasa"}},
	{ID: "csa-al", Name: "CSA", State: "AL", Country: "BRA",
		Aliases: []string{"CSA", "Csa-AL", "Centro Sportivo Alagoano"}},
	{ID: "crb-al", Name: "CRB", State: "AL", Country: "BRA", Aliases: []string{"CRB", "CRB - AL"}},
	{ID: "asa-al", Name: "ASA", State: "AL", Country: "BRA", Aliases: []string{"ASA", "ASA AL", "A.s.a. - AL"}},
	{ID: "confianca-se", Name: "Confiança", State: "SE", Country: "BRA",
		Aliases: []string{"Confianca", "Confiança", "AD Confianca", "AD Confiança"}},
	{ID: "sampaio-correa-ma", Name: "Sampaio Corrêa", State: "MA", Country: "BRA",
		Aliases: []string{"Sampaio Correa", "Sampaio Corrêa"}},
	{ID: "abc-rn", Name: "ABC", State: "RN", Country: "BRA",
		Aliases: []string{"ABC", "ABC - RN", "A.b.c. - RN"}},
	{ID: "america-rn", Name: "América-RN", State: "RN", Country: "BRA",
		Aliases: []string{"America-RN", "América-RN", "America RN", "América - RN", "America FC Natal"}},
	{ID: "botafogo-pb", Name: "Botafogo-PB", State: "PB", Country: "BRA",
		Aliases: []string{"Botafogo-PB", "Botafogo PB", "Botafogo - PB"}},
	{ID: "botafogo-sp", Name: "Botafogo-SP", State: "SP", Country: "BRA",
		Aliases: []string{"Botafogo-SP", "Botafogo SP", "Botafogo - SP"}},
	{ID: "paysandu-pa", Name: "Paysandu", State: "PA", Country: "BRA",
		Aliases: []string{"Paysandu", "Paysandu SC"}},
	{ID: "remo-pa", Name: "Remo", State: "PA", Country: "BRA",
		Aliases: []string{"Remo", "Clube Do Remo", "Clube do Remo"}},

	// ---- Santa Catarina -----------------------------------------------------
	{ID: "chapecoense-sc", Name: "Chapecoense", State: "SC", Country: "BRA",
		Aliases: []string{"Chapecoense", "Chapecoense-SC", "Associação Chapecoense de Futebol"}},
	{ID: "avai-sc", Name: "Avaí", State: "SC", Country: "BRA", Aliases: []string{"Avai", "Avaí", "Avai-SC", "Avaí FC"}},
	{ID: "figueirense-sc", Name: "Figueirense", State: "SC", Country: "BRA",
		Aliases: []string{"Figueirense", "Figueirense-SC", "Figueirense FC"}},
	{ID: "criciuma-sc", Name: "Criciúma", State: "SC", Country: "BRA",
		Aliases: []string{"Criciuma", "Criciúma", "Criciuma-SC", "Criciúma EC"}},
	{ID: "joinville-sc", Name: "Joinville", State: "SC", Country: "BRA",
		Aliases: []string{"Joinville", "Joinville-SC", "Joinville EC"}},
	{ID: "brusque-sc", Name: "Brusque", State: "SC", Country: "BRA", Aliases: []string{"Brusque", "Brusque FC"}},

	// ---- South America (only where the raw spellings need disambiguation) ----
	{ID: "river-plate-arg", Name: "River Plate", Country: "ARG",
		Aliases: []string{"River Plate", "CA River Plate"}},
	{ID: "river-plate-uru", Name: "River Plate (URU)", Country: "URU", Aliases: []string{"River Plate-URU", "River Plate (URU)"}},
	{ID: "boca-juniors-arg", Name: "Boca Juniors", Country: "ARG", Aliases: []string{"Boca Juniors", "CA Boca Juniors"}},
	{ID: "racing-arg", Name: "Racing Club", Country: "ARG", Aliases: []string{"Racing Club", "Racing Club de Avellaneda"}},
	{ID: "independiente-arg", Name: "Independiente", Country: "ARG", Aliases: []string{"Independiente", "CA Independiente"}},
	{ID: "san-lorenzo-arg", Name: "San Lorenzo", Country: "ARG", Aliases: []string{"San Lorenzo", "CA San Lorenzo de Almagro"}},
	{ID: "velez-arg", Name: "Vélez Sarsfield", Country: "ARG", Aliases: []string{"Velez Sarsfield", "Vélez Sarsfield"}},
	{ID: "estudiantes-arg", Name: "Estudiantes", Country: "ARG", Aliases: []string{"Estudiantes", "Estudiantes de La Plata"}},
	{ID: "newells-arg", Name: "Newell's Old Boys", Country: "ARG", Aliases: []string{"Newells Old Boys", "Newell's Old Boys"}},
	{ID: "nacional-uru", Name: "Nacional (URU)", Country: "URU",
		Aliases: []string{"Nacional (URU)", "Nacional-URU", "Club Nacional de Football"}},
	{ID: "penarol-uru", Name: "Peñarol", Country: "URU", Aliases: []string{"Penarol", "Peñarol", "CA Peñarol"}},
	{ID: "nacional-par", Name: "Nacional (PAR)", Country: "PAR", Aliases: []string{"Nacional (PAR)", "Nacional-PAR"}},
	{ID: "guarani-par", Name: "Guaraní (PAR)", Country: "PAR", Aliases: []string{"Guarani (PAR)", "Guaraní (PAR)", "Guarani-PAR", "Guaraní-PAR"}},
	{ID: "libertad-par", Name: "Libertad", Country: "PAR", Aliases: []string{"Libertad", "Libertad-PAR"}},
	{ID: "olimpia-par", Name: "Olimpia", Country: "PAR", Aliases: []string{"Olimpia", "Olimpia-PAR"}},
	{ID: "cerro-porteno-par", Name: "Cerro Porteño", Country: "PAR", Aliases: []string{"Cerro Porteno", "Cerro Porteño"}},
	{ID: "universitario-per", Name: "Universitario", Country: "PER", Aliases: []string{"Universitario (PER)", "Universitario-PER"}},
	{ID: "sporting-cristal-per", Name: "Sporting Cristal", Country: "PER", Aliases: []string{"Sporting Cristal"}},
	{ID: "alianza-lima-per", Name: "Alianza Lima", Country: "PER", Aliases: []string{"Alianza Lima"}},
	{ID: "barcelona-equ", Name: "Barcelona SC (EQU)", Country: "ECU", Aliases: []string{"Barcelona-EQU", "Barcelona SC (EQU)"}},
	{ID: "delfin-equ", Name: "Delfín", Country: "ECU", Aliases: []string{"Delfin", "Delfín", "Delfin-EQU", "Delfín-EQU"}},
	{ID: "ldu-equ", Name: "LDU Quito", Country: "ECU", Aliases: []string{"LDU", "LDU Quito", "LDU-EQU"}},
	{ID: "emelec-equ", Name: "Emelec", Country: "ECU", Aliases: []string{"Emelec"}},
	{ID: "independiente-del-valle-equ", Name: "Independiente del Valle", Country: "ECU",
		Aliases: []string{"Independiente del Valle", "Independiente Del Valle"}},
	{ID: "colo-colo-chi", Name: "Colo-Colo", Country: "CHI", Aliases: []string{"Colo-Colo", "Colo Colo"}},
	{ID: "universidad-catolica-chi", Name: "Universidad Católica", Country: "CHI", Aliases: []string{"Universidad Catolica", "Universidad Católica"}},
	{ID: "universidad-de-chile-chi", Name: "Universidad de Chile", Country: "CHI", Aliases: []string{"Universidad de Chile"}},
	{ID: "bolivar-bol", Name: "Bolívar", Country: "BOL", Aliases: []string{"Bolivar", "Bolívar"}},
	{ID: "the-strongest-bol", Name: "The Strongest", Country: "BOL", Aliases: []string{"The Strongest"}},
	{ID: "atletico-nacional-col", Name: "Atlético Nacional", Country: "COL", Aliases: []string{"Atletico Nacional", "Atlético Nacional"}},
	{ID: "santa-fe-col", Name: "Independiente Santa Fe", Country: "COL",
		Aliases: []string{"Ind. Santa Fe", "Independiente Santa Fe", "Santa Fe"}},
	{ID: "tolima-col", Name: "Deportes Tolima", Country: "COL", Aliases: []string{"Tolima", "Deportes Tolima"}},
	{ID: "junior-col", Name: "Junior", Country: "COL", Aliases: []string{"Junior de Barranquilla", "Junior"}},
	{ID: "millonarios-col", Name: "Millonarios", Country: "COL", Aliases: []string{"Millonarios"}},
	{ID: "america-de-cali-col", Name: "América de Cali", Country: "COL", Aliases: []string{"America de Cali", "América de Cali"}},
	{ID: "deportivo-cali-col", Name: "Deportivo Cali", Country: "COL", Aliases: []string{"Deportivo Cali"}},
	{ID: "caracas-ven", Name: "Caracas", Country: "VEN", Aliases: []string{"Caracas", "Caracas FC"}},
	{ID: "zamora-ven", Name: "Zamora", Country: "VEN", Aliases: []string{"Zamora", "Zamora FC"}},
	{ID: "deportivo-tachira-ven", Name: "Deportivo Táchira", Country: "VEN", Aliases: []string{"Deportivo Tachira", "Deportivo Táchira"}},
	{ID: "toluca-mex", Name: "Toluca", Country: "MEX", Aliases: []string{"Toluca", "Deportivo Toluca"}},
	{ID: "tijuana-mex", Name: "Tijuana", Country: "MEX", Aliases: []string{"Tijuana", "Club Tijuana"}},
	{ID: "pumas-mex", Name: "Pumas UNAM", Country: "MEX", Aliases: []string{"Pumas", "Pumas UNAM"}},
	{ID: "tigres-mex", Name: "Tigres UANL", Country: "MEX", Aliases: []string{"Tigres", "Tigres UANL"}},
	{ID: "santos-laguna-mex", Name: "Santos Laguna", Country: "MEX", Aliases: []string{"Santos Laguna"}},
	{ID: "atlas-mex", Name: "Atlas", Country: "MEX", Aliases: []string{"Atlas", "Atlas FC"}},
	{ID: "leon-mex", Name: "León", Country: "MEX", Aliases: []string{"Leon", "León", "Club León"}},
}

// ---------------------------------------------------------------------------
// Competitions
// ---------------------------------------------------------------------------

// Competition describes one tournament present in the data.
type Competition struct {
	ID      string `json:"id"`
	Name    string `json:"name"`
	Short   string `json:"short_name"`
	Kind    string `json:"kind"`   // league | cup | continental
	Format  string `json:"format"` // double_round_robin | group_knockout
	Country string `json:"country"`
	Tier    int    `json:"tier,omitempty"`
}

// Competition formats. Only a double round robin can be turned into a single
// table with a champion and a relegation zone; Série C and the continental
// tournaments run groups followed by knockouts.
const (
	FormatDoubleRoundRobin = "double_round_robin"
	FormatGroupKnockout    = "group_knockout"
	FormatKnockout         = "knockout"
)

// Competition identifiers used throughout the package.
const (
	CompBrasileirao  = "brasileirao"
	CompSerieB       = "serie-b"
	CompSerieC       = "serie-c"
	CompCopaDoBrasil = "copa-do-brasil"
	CompLibertadores = "libertadores"
)

var competitionList = []Competition{
	{ID: CompBrasileirao, Name: "Campeonato Brasileiro Série A", Short: "Brasileirão", Kind: "league", Format: FormatDoubleRoundRobin, Country: "BRA", Tier: 1},
	{ID: CompSerieB, Name: "Campeonato Brasileiro Série B", Short: "Série B", Kind: "league", Format: FormatDoubleRoundRobin, Country: "BRA", Tier: 2},
	{ID: CompSerieC, Name: "Campeonato Brasileiro Série C", Short: "Série C", Kind: "league", Format: FormatGroupKnockout, Country: "BRA", Tier: 3},
	{ID: CompCopaDoBrasil, Name: "Copa do Brasil", Short: "Copa do Brasil", Kind: "cup", Format: FormatKnockout, Country: "BRA"},
	{ID: CompLibertadores, Name: "CONMEBOL Copa Libertadores", Short: "Libertadores", Kind: "continental", Format: FormatGroupKnockout, Country: "CONMEBOL"},
}

// competitionAliases maps everything a user (or an LLM) might type onto a
// competition id.
var competitionAliases = map[string]string{
	"brasileirao": CompBrasileirao, "brasileirao serie a": CompBrasileirao,
	"campeonato brasileiro": CompBrasileirao, "campeonato brasileiro serie a": CompBrasileirao,
	"serie a": CompBrasileirao, "seriea": CompBrasileirao, "brazilian league": CompBrasileirao,
	"brazilian serie a": CompBrasileirao, "brasileirao a": CompBrasileirao, "league": CompBrasileirao,
	"serie b": CompSerieB, "brasileirao serie b": CompSerieB, "campeonato brasileiro serie b": CompSerieB,
	"serie c": CompSerieC, "brasileirao serie c": CompSerieC, "campeonato brasileiro serie c": CompSerieC,
	"copa do brasil": CompCopaDoBrasil, "brazilian cup": CompCopaDoBrasil, "cup": CompCopaDoBrasil,
	"copa brasil": CompCopaDoBrasil, "brazil cup": CompCopaDoBrasil,
	"libertadores": CompLibertadores, "copa libertadores": CompLibertadores,
	"conmebol libertadores": CompLibertadores, "copa conmebol libertadores": CompLibertadores,
}

// ResolveCompetition maps free text onto a competition id.
func ResolveCompetition(q string) (string, bool) {
	f := strings.Join(strings.Fields(Fold(q)), " ")
	if f == "" {
		return "", false
	}
	if id, ok := competitionAliases[f]; ok {
		return id, true
	}
	for _, c := range competitionList {
		if Fold(c.ID) == f || Fold(c.Name) == f || Fold(c.Short) == f {
			return c.ID, true
		}
	}
	// Fall back to a unique prefix match ("libertad" -> libertadores).
	var hit string
	var n int
	for alias, id := range competitionAliases {
		if strings.HasPrefix(alias, f) {
			if hit == "" || hit == id {
				hit = id
				continue
			}
			n++
		}
	}
	if hit != "" && n == 0 {
		return hit, true
	}
	return "", false
}

// Competitions returns the catalogue of competitions.
func Competitions() []Competition {
	out := make([]Competition, len(competitionList))
	copy(out, competitionList)
	return out
}

// CompetitionByID looks a competition up.
func CompetitionByID(id string) (Competition, bool) {
	for _, c := range competitionList {
		if c.ID == id {
			return c, true
		}
	}
	return Competition{}, false
}

// ---------------------------------------------------------------------------
// Derbies
// ---------------------------------------------------------------------------

// Rivalry names a traditional derby between two canonical clubs.
type Rivalry struct {
	Name  string `json:"name"`
	TeamA string `json:"team_a"`
	TeamB string `json:"team_b"`
	Note  string `json:"note,omitempty"`
}

var rivalries = []Rivalry{
	{Name: "Fla-Flu", TeamA: "flamengo-rj", TeamB: "fluminense-rj", Note: "Rio de Janeiro"},
	{Name: "Clássico dos Milhões", TeamA: "flamengo-rj", TeamB: "vasco-rj", Note: "Rio de Janeiro"},
	{Name: "Clássico da Rivalidade", TeamA: "botafogo-rj", TeamB: "flamengo-rj", Note: "Rio de Janeiro"},
	{Name: "Clássico Vovô", TeamA: "botafogo-rj", TeamB: "fluminense-rj", Note: "Rio de Janeiro"},
	{Name: "Clássico dos Gigantes", TeamA: "botafogo-rj", TeamB: "vasco-rj", Note: "Rio de Janeiro"},
	{Name: "Clássico dos Clássicos (RJ)", TeamA: "fluminense-rj", TeamB: "vasco-rj", Note: "Rio de Janeiro"},
	{Name: "Derby Paulista", TeamA: "corinthians-sp", TeamB: "palmeiras-sp", Note: "São Paulo"},
	{Name: "Majestoso", TeamA: "corinthians-sp", TeamB: "sao-paulo-sp", Note: "São Paulo"},
	{Name: "Choque-Rei", TeamA: "palmeiras-sp", TeamB: "sao-paulo-sp", Note: "São Paulo"},
	{Name: "Clássico Alvinegro", TeamA: "corinthians-sp", TeamB: "santos-sp", Note: "São Paulo"},
	{Name: "Clássico da Saudade", TeamA: "palmeiras-sp", TeamB: "santos-sp", Note: "São Paulo"},
	{Name: "San-São", TeamA: "santos-sp", TeamB: "sao-paulo-sp", Note: "São Paulo"},
	{Name: "Grenal", TeamA: "gremio-rs", TeamB: "internacional-rs", Note: "Rio Grande do Sul"},
	{Name: "Clássico Mineiro", TeamA: "atletico-mg", TeamB: "cruzeiro-mg", Note: "Minas Gerais"},
	{Name: "Atletiba", TeamA: "athletico-pr", TeamB: "coritiba-pr", Note: "Paraná"},
	{Name: "Ba-Vi", TeamA: "bahia-ba", TeamB: "vitoria-ba", Note: "Bahia"},
	{Name: "Clássico dos Clássicos (PE)", TeamA: "nautico-pe", TeamB: "sport-pe", Note: "Pernambuco"},
	{Name: "Clássico das Multidões", TeamA: "santa-cruz-pe", TeamB: "sport-pe", Note: "Pernambuco"},
	{Name: "Clássico Rei", TeamA: "ceara-ce", TeamB: "fortaleza-ce", Note: "Ceará"},
	{Name: "Derby Goiano", TeamA: "atletico-go", TeamB: "goias-go", Note: "Goiás"},
	{Name: "Clássico da Capital", TeamA: "avai-sc", TeamB: "figueirense-sc", Note: "Santa Catarina"},
	{Name: "Clássico Mineiro (América)", TeamA: "america-mg", TeamB: "atletico-mg", Note: "Minas Gerais"},
}

// Rivalries returns the curated derby table.
func Rivalries() []Rivalry {
	out := make([]Rivalry, len(rivalries))
	copy(out, rivalries)
	return out
}

// RivalryFor returns the derby name for a pair of team ids, if any.
func RivalryFor(a, b string) (Rivalry, bool) {
	for _, r := range rivalries {
		if (r.TeamA == a && r.TeamB == b) || (r.TeamA == b && r.TeamB == a) {
			return r, true
		}
	}
	return Rivalry{}, false
}
