// clubs.go - the curated club identity table.
//
// Context
//
//	normalize.go reduces raw team spellings mechanically, but some variations
//	cannot be derived from the string alone:
//
//	    "Vasco"                 == "Vasco da Gama-RJ"
//	    "Athletico"             == "Atlético-PR" == "Athletico Paranaense - PR"
//	    "Sport Club do Recife"  == "Sport-PE"
//	    "Red Bull Bragantino"   == "Bragantino - SP"
//	    "Santos"                != "Santos - AP"
//
//	knownClubs pins those identities down for every club that has appeared in
//	the Série A era plus the ambiguous smaller clubs, giving each a stable ID,
//	a display name with correct Portuguese orthography, and its state.
//
//	Lookup order (see resolver.go):
//	  1. exact "base|REGION" key      - "atletico|PR"      -> atletico-pr
//	  2. region-agnostic base key     - "vasco gama"       -> vasco-da-gama-rj
//	     but only when the parsed region agrees with the club's state, so that
//	     "Santos - AP" does not collapse into Santos FC.
//	  3. the statistical registry built from the data itself.
package soccer

// knownClub is one hand-curated entry of the club identity table.
type knownClub struct {
	ID      string
	Name    string
	State   string
	Country string
	// Aliases are raw spellings as they occur across the datasets, plus
	// spellings a user is likely to type.
	Aliases []string
}

// knownClubs is ordered: when two clubs would claim the same region-agnostic
// base name, the first entry wins (so bare "Atlético" means Galo, bare
// "Flamengo" means the Rio club).
var knownClubs = []knownClub{
	{ID: "flamengo-rj", Name: "Flamengo", State: "RJ", Country: "Brazil",
		Aliases: []string{"Flamengo", "Flamengo-RJ", "Flamengo - RJ", "CR Flamengo", "Clube de Regatas do Flamengo"}},
	{ID: "palmeiras-sp", Name: "Palmeiras", State: "SP", Country: "Brazil",
		Aliases: []string{"Palmeiras", "Palmeiras-SP", "Palmeiras - SP", "SE Palmeiras"}},
	{ID: "corinthians-sp", Name: "Corinthians", State: "SP", Country: "Brazil",
		Aliases: []string{"Corinthians", "Corinthians-SP", "Corinthians - SP", "Sport Club Corinthians Paulista"}},
	{ID: "sao-paulo-sp", Name: "São Paulo", State: "SP", Country: "Brazil",
		Aliases: []string{"São Paulo", "Sao Paulo", "Sao Paulo-SP", "São Paulo - SP", "São Paulo FC", "Sao Paulo FC"}},
	{ID: "santos-sp", Name: "Santos", State: "SP", Country: "Brazil",
		Aliases: []string{"Santos", "Santos-SP", "Santos - SP", "Santos FC"}},
	{ID: "fluminense-rj", Name: "Fluminense", State: "RJ", Country: "Brazil",
		Aliases: []string{"Fluminense", "Fluminense-RJ", "Fluminense - RJ", "Fluminense RJ", "Fluminense FC"}},
	{ID: "botafogo-rj", Name: "Botafogo", State: "RJ", Country: "Brazil",
		Aliases: []string{"Botafogo", "Botafogo-RJ", "Botafogo - RJ", "Botafogo RJ", "Botafogo de Futebol e Regatas"}},
	{ID: "vasco-da-gama-rj", Name: "Vasco da Gama", State: "RJ", Country: "Brazil",
		Aliases: []string{"Vasco", "Vasco da Gama", "Vasco da Gama-RJ", "Vasco da Gama - RJ", "Vasco Da Gama RJ", "CR Vasco da Gama"}},
	{ID: "gremio-rs", Name: "Grêmio", State: "RS", Country: "Brazil",
		Aliases: []string{"Grêmio", "Gremio", "Gremio-RS", "Grêmio - RS", "Gremio RS", "Grêmio FBPA"}},
	{ID: "internacional-rs", Name: "Internacional", State: "RS", Country: "Brazil",
		Aliases: []string{"Internacional", "Internacional-RS", "Internacional - RS", "Internacional RS", "Inter", "SC Internacional"}},
	{ID: "cruzeiro-mg", Name: "Cruzeiro", State: "MG", Country: "Brazil",
		Aliases: []string{"Cruzeiro", "Cruzeiro-MG", "Cruzeiro - MG", "Cruzeiro EC"}},
	{ID: "atletico-mg", Name: "Atlético Mineiro", State: "MG", Country: "Brazil",
		Aliases: []string{"Atlético Mineiro", "Atletico Mineiro", "Atlético-MG", "Atletico-MG", "Atlético - MG",
			"Atletico - MG", "Atlético Mineiro - MG", "Atlético", "Atletico", "Galo"}},
	{ID: "atletico-pr", Name: "Athletico Paranaense", State: "PR", Country: "Brazil",
		Aliases: []string{"Athletico", "Athletico Paranaense", "Atletico Paranaense", "Athletico-PR", "Atlético-PR",
			"Atletico-PR", "Atlético - PR", "Atletico - PR", "Athletico Paranaense - PR", "Atlético Paranaense - PR",
			"Atlético Paranaense", "Furacão"}},
	{ID: "atletico-go", Name: "Atlético Goianiense", State: "GO", Country: "Brazil",
		Aliases: []string{"Atlético Goianiense", "Atletico Goianiense", "Atlético-GO", "Atletico-GO", "Atlético - GO", "Atletico - GO"}},
	{ID: "atletico-ac", Name: "Atlético Acreano", State: "AC", Country: "Brazil",
		Aliases: []string{"Atlético Acreano", "Atletico Acreano", "Atlético - AC"}},
	{ID: "atletico-ce", Name: "Atlético Cearense", State: "CE", Country: "Brazil",
		Aliases: []string{"Atlético Cearense", "FC Atlético Cearense", "Atlético Cearense - CE", "Uniclinic - CE", "Uniclinic CE"}},
	{ID: "atletico-ba", Name: "Atlético de Alagoinhas", State: "BA", Country: "Brazil",
		Aliases: []string{"Atlético Alagoinhas", "Atletico Alagoinhas", "Atlético - BA"}},
	{ID: "atletico-es", Name: "Atlético Itapemirim", State: "ES", Country: "Brazil",
		Aliases: []string{"Atletico - ES", "Atlético - ES"}},
	{ID: "bahia-ba", Name: "Bahia", State: "BA", Country: "Brazil",
		Aliases: []string{"Bahia", "Bahia-BA", "Bahia - BA", "EC Bahia"}},
	{ID: "vitoria-ba", Name: "Vitória", State: "BA", Country: "Brazil",
		Aliases: []string{"Vitória", "Vitoria", "Vitoria-BA", "Vitória - BA", "EC Vitoria", "Vitoria EC"}},
	{ID: "sport-pe", Name: "Sport Recife", State: "PE", Country: "Brazil",
		Aliases: []string{"Sport", "Sport-PE", "Sport - PE", "Sport Recife", "Sport Club do Recife"}},
	{ID: "nautico-pe", Name: "Náutico", State: "PE", Country: "Brazil",
		Aliases: []string{"Náutico", "Nautico", "Nautico-PE", "Náutico - PE", "Nautico Capibaribe"}},
	{ID: "santa-cruz-pe", Name: "Santa Cruz", State: "PE", Country: "Brazil",
		Aliases: []string{"Santa Cruz", "Santa Cruz-PE", "Santa Cruz - PE", "Santa Cruz FC"}},
	{ID: "ceara-ce", Name: "Ceará", State: "CE", Country: "Brazil",
		Aliases: []string{"Ceará", "Ceara", "Ceara-CE", "Ceará - CE", "Ceará Sporting Club"}},
	{ID: "fortaleza-ce", Name: "Fortaleza", State: "CE", Country: "Brazil",
		Aliases: []string{"Fortaleza", "Fortaleza-CE", "Fortaleza - CE", "Fortaleza EC", "Fortaleza FC"}},
	{ID: "goias-go", Name: "Goiás", State: "GO", Country: "Brazil",
		Aliases: []string{"Goiás", "Goias", "Goias-GO", "Goiás - GO"}},
	{ID: "vila-nova-go", Name: "Vila Nova", State: "GO", Country: "Brazil",
		Aliases: []string{"Vila Nova", "Vila Nova - GO", "Vila Nova GO"}},
	{ID: "coritiba-pr", Name: "Coritiba", State: "PR", Country: "Brazil",
		Aliases: []string{"Coritiba", "Coritiba-PR", "Coritiba - PR", "Coritiba PR"}},
	{ID: "parana-pr", Name: "Paraná", State: "PR", Country: "Brazil",
		Aliases: []string{"Paraná", "Parana", "Parana-PR", "Paraná - PR", "CA Parana", "Paraná Clube"}},
	{ID: "londrina-pr", Name: "Londrina", State: "PR", Country: "Brazil",
		Aliases: []string{"Londrina", "Londrina - PR"}},
	{ID: "chapecoense-sc", Name: "Chapecoense", State: "SC", Country: "Brazil",
		Aliases: []string{"Chapecoense", "Chapecoense-SC", "Chapecoense - SC"}},
	{ID: "avai-sc", Name: "Avaí", State: "SC", Country: "Brazil",
		Aliases: []string{"Avaí", "Avai", "Avai-SC", "Avaí - SC"}},
	{ID: "figueirense-sc", Name: "Figueirense", State: "SC", Country: "Brazil",
		Aliases: []string{"Figueirense", "Figueirense-SC", "Figueirense - SC"}},
	{ID: "criciuma-sc", Name: "Criciúma", State: "SC", Country: "Brazil",
		Aliases: []string{"Criciúma", "Criciuma", "Criciuma-SC", "Criciúma - SC", "Criciuma - SC"}},
	{ID: "joinville-sc", Name: "Joinville", State: "SC", Country: "Brazil",
		Aliases: []string{"Joinville", "Joinville-SC", "Joinville - SC"}},
	{ID: "juventude-rs", Name: "Juventude", State: "RS", Country: "Brazil",
		Aliases: []string{"Juventude", "Juventude-RS", "Juventude - RS", "EC Juventude"}},
	{ID: "caxias-rs", Name: "Caxias", State: "RS", Country: "Brazil",
		Aliases: []string{"Caxias", "Caxias - RS", "Caxias RS", "Ser Caxias"}},
	{ID: "ponte-preta-sp", Name: "Ponte Preta", State: "SP", Country: "Brazil",
		Aliases: []string{"Ponte Preta", "Ponte Preta-SP", "Ponte Preta - SP"}},
	{ID: "portuguesa-sp", Name: "Portuguesa", State: "SP", Country: "Brazil",
		Aliases: []string{"Portuguesa", "Portuguesa-SP", "Portuguesa - SP", "Portuguesa Desportos"}},
	{ID: "bragantino-sp", Name: "Red Bull Bragantino", State: "SP", Country: "Brazil",
		Aliases: []string{"Bragantino", "Bragantino - SP", "Red Bull Bragantino", "Red Bull Bragantino-SP", "Red Bull Bragantino - SP"}},
	{ID: "guarani-sp", Name: "Guarani", State: "SP", Country: "Brazil",
		Aliases: []string{"Guarani", "Guarani - SP", "Guarani SP", "Guarani-SP"}},
	{ID: "santo-andre-sp", Name: "Santo André", State: "SP", Country: "Brazil",
		Aliases: []string{"Santo André", "Santo Andre", "Santo André - SP", "Santo Andre SP"}},
	{ID: "sao-caetano-sp", Name: "São Caetano", State: "SP", Country: "Brazil",
		Aliases: []string{"São Caetano", "Sao Caetano", "São Caetano - SP"}},
	{ID: "america-mg", Name: "América Mineiro", State: "MG", Country: "Brazil",
		Aliases: []string{"América-MG", "America-MG", "América - MG", "America - MG", "America MG",
			"América FC (Minas Gerais)", "América Mineiro", "America"}},
	{ID: "america-rn", Name: "América de Natal", State: "RN", Country: "Brazil",
		Aliases: []string{"América - RN", "America RN", "América de Natal - RN", "America FC Natal", "América de Natal"}},
	{ID: "tombense-mg", Name: "Tombense", State: "MG", Country: "Brazil",
		Aliases: []string{"Tombense", "Tombense - MG", "Tombense MG"}},
	{ID: "csa-al", Name: "CSA", State: "AL", Country: "Brazil",
		Aliases: []string{"CSA", "Csa-AL", "Csa - AL", "C.s.a. - AL", "CS Alagoano"}},
	{ID: "crb-al", Name: "CRB", State: "AL", Country: "Brazil",
		Aliases: []string{"CRB", "Crb - AL", "C.r.b. - AL", "C. R. B. - AL"}},
	{ID: "cuiaba-mt", Name: "Cuiabá", State: "MT", Country: "Brazil",
		Aliases: []string{"Cuiabá", "Cuiaba", "Cuiaba-MT", "Cuiabá - MT", "Cuiaba MT"}},
	{ID: "brasiliense-df", Name: "Brasiliense", State: "DF", Country: "Brazil",
		Aliases: []string{"Brasiliense", "Brasiliense - DF"}},
	{ID: "paysandu-pa", Name: "Paysandu", State: "PA", Country: "Brazil",
		Aliases: []string{"Paysandu", "Paysandu - PA"}},
	{ID: "remo-pa", Name: "Remo", State: "PA", Country: "Brazil",
		Aliases: []string{"Remo", "Remo - PA", "Remo PA", "Clube Do Remo"}},
	{ID: "ipatinga-mg", Name: "Ipatinga", State: "MG", Country: "Brazil",
		Aliases: []string{"Ipatinga", "Ipatinga - MG"}},
	{ID: "barueri-sp", Name: "Grêmio Barueri", State: "SP", Country: "Brazil",
		Aliases: []string{"Barueri", "Grêmio Barueri", "Grêmio Barueri - SP", "Grêmio Prudente"}},
	{ID: "abc-rn", Name: "ABC", State: "RN", Country: "Brazil",
		Aliases: []string{"ABC", "Abc - RN", "A.b.c. - RN"}},
	{ID: "novorizontino-sp", Name: "Novorizontino", State: "SP", Country: "Brazil",
		Aliases: []string{"Novorizontino", "Novorizontino - SP", "Gremio Novorizontino"}},
	{ID: "operario-pr", Name: "Operário Ferroviário", State: "PR", Country: "Brazil",
		Aliases: []string{"Operário - PR", "Operario PR", "Operario - PR", "Operario Ferroviario Esporte C - PR"}},
	{ID: "confianca-se", Name: "Confiança", State: "SE", Country: "Brazil",
		Aliases: []string{"Confiança", "Confianca", "AD Confianca", "Confiança - SE", "Confianca SE"}},
	{ID: "sampaio-correa-ma", Name: "Sampaio Corrêa", State: "MA", Country: "Brazil",
		Aliases: []string{"Sampaio Corrêa", "Sampaio Correa", "Sampaio Corrêa - MA", "Sampaio Correa - MA"}},
	{ID: "brasil-de-pelotas-rs", Name: "Brasil de Pelotas", State: "RS", Country: "Brazil",
		Aliases: []string{"Brasil de Pelotas", "Brasil - RS"}},
	{ID: "oeste-sp", Name: "Oeste", State: "SP", Country: "Brazil",
		Aliases: []string{"Oeste", "Oeste - SP"}},
	{ID: "boa-mg", Name: "Boa Esporte", State: "MG", Country: "Brazil",
		Aliases: []string{"Boa", "Boa - MG"}},
	{ID: "luverdense-mt", Name: "Luverdense", State: "MT", Country: "Brazil",
		Aliases: []string{"Luverdense", "Luverdense - MT"}},
	{ID: "manaus-am", Name: "Manaus", State: "AM", Country: "Brazil",
		Aliases: []string{"Manaus", "Manaus - AM"}},
	{ID: "volta-redonda-rj", Name: "Volta Redonda", State: "RJ", Country: "Brazil",
		Aliases: []string{"Volta Redonda", "Volta Redonda - RJ"}},
	{ID: "brusque-sc", Name: "Brusque", State: "SC", Country: "Brazil",
		Aliases: []string{"Brusque", "Brusque - SC"}},
	{ID: "ituano-sp", Name: "Ituano", State: "SP", Country: "Brazil",
		Aliases: []string{"Ituano", "Ituano - SP"}},
	{ID: "mirassol-sp", Name: "Mirassol", State: "SP", Country: "Brazil",
		Aliases: []string{"Mirassol", "Mirassol - SP"}},
	{ID: "boavista-rj", Name: "Boavista", State: "RJ", Country: "Brazil",
		Aliases: []string{"Boavista", "Boavista - RJ", "Boavista RJ", "Boavista SC Saquarema",
			"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"}},
	{ID: "moto-club-ma", Name: "Moto Club", State: "MA", Country: "Brazil",
		Aliases: []string{"Moto Club - MA", "Moto Clube", "Moto Club de São Luís"}},
	{ID: "ferroviario-ce", Name: "Ferroviário", State: "CE", Country: "Brazil",
		Aliases: []string{"Ferroviário - CE", "Ferroviario"}},
	{ID: "sao-bento-sp", Name: "São Bento", State: "SP", Country: "Brazil",
		Aliases: []string{"São Bento - SP", "Sao Bento"}},

	// CONMEBOL clubs that appear in the Libertadores dataset and need their
	// country pinned so that homonyms stay apart.
	{ID: "river-plate-arg", Name: "River Plate", State: "ARG", Country: "Argentina",
		Aliases: []string{"River Plate", "River Plate-ARG", "CA River Plate"}},
	{ID: "river-plate-uru", Name: "River Plate (Montevideo)", State: "URU", Country: "Uruguay",
		Aliases: []string{"River Plate-URU", "River Plate (URU)"}},
	{ID: "nacional-uru", Name: "Nacional (Uruguay)", State: "URU", Country: "Uruguay",
		Aliases: []string{"Nacional (URU)", "Nacional-URU"}},
	{ID: "nacional-par", Name: "Nacional (Paraguay)", State: "PAR", Country: "Paraguay",
		Aliases: []string{"Nacional (PAR)", "Nacional-PAR"}},
	{ID: "guarani-par", Name: "Guaraní (Paraguay)", State: "PAR", Country: "Paraguay",
		Aliases: []string{"Guaraní (PAR)", "Guaraní-PAR", "Guarani-PAR"}},
	{ID: "libertad-par", Name: "Libertad", State: "PAR", Country: "Paraguay",
		Aliases: []string{"Libertad", "Libertad-PAR"}},
	{ID: "olimpia-par", Name: "Olimpia", State: "PAR", Country: "Paraguay",
		Aliases: []string{"Olimpia", "Olimpia-PAR"}},
	{ID: "barcelona-equ", Name: "Barcelona SC (Ecuador)", State: "EQU", Country: "Ecuador",
		Aliases: []string{"Barcelona-EQU", "Barcelona (EQU)"}},
	{ID: "delfin-equ", Name: "Delfín", State: "EQU", Country: "Ecuador",
		Aliases: []string{"Delfín", "Delfín-EQU"}},
	{ID: "universitario-per", Name: "Universitario", State: "PER", Country: "Peru",
		Aliases: []string{"Universitario (PER)", "Universitario-PER"}},
	{ID: "boca-juniors-arg", Name: "Boca Juniors", State: "ARG", Country: "Argentina",
		Aliases: []string{"Boca Juniors", "CA Boca Juniors"}},
	{ID: "penarol-uru", Name: "Peñarol", State: "URU", Country: "Uruguay",
		Aliases: []string{"Peñarol", "Penarol"}},
	{ID: "colo-colo-chi", Name: "Colo-Colo", State: "CHI", Country: "Chile",
		Aliases: []string{"Colo-Colo", "Colo Colo"}},
	{ID: "independiente-del-valle-equ", Name: "Independiente del Valle", State: "EQU", Country: "Ecuador",
		Aliases: []string{"Independiente del Valle", "Independiente Del Valle"}},
}

// fifaClubToClubID links the 15 Brazilian domestic clubs present in
// fifa_data.csv to their knowledge-graph club nodes. The mapping is explicit
// rather than fuzzy: several European clubs in the FIFA data ("CD Nacional",
// "Sporting CP") would otherwise be matched to Brazilian homonyms.
var fifaClubToClubID = map[string]string{
	"Grêmio":                    "gremio-rs",
	"Atlético Mineiro":          "atletico-mg",
	"Cruzeiro":                  "cruzeiro-mg",
	"Fluminense":                "fluminense-rj",
	"Santos":                    "santos-sp",
	"Internacional":             "internacional-rs",
	"América FC (Minas Gerais)": "america-mg",
	"Botafogo":                  "botafogo-rj",
	"Bahia":                     "bahia-ba",
	"Paraná":                    "parana-pr",
	"Atlético Paranaense":       "atletico-pr",
	"Vitória":                   "vitoria-ba",
	"Sport Club do Recife":      "sport-pe",
	"Chapecoense":               "chapecoense-sc",
	"Ceará Sporting Club":       "ceara-ce",
}

// classicRivalries drives the "derby" queries. Each entry is a pair of club
// IDs plus the popular name of the fixture.
var classicRivalries = []struct {
	A, B string
	Name string
}{
	{"flamengo-rj", "fluminense-rj", "Fla-Flu"},
	{"flamengo-rj", "vasco-da-gama-rj", "Clássico dos Milhões"},
	{"flamengo-rj", "botafogo-rj", "Clássico da Rivalidade"},
	{"botafogo-rj", "vasco-da-gama-rj", "Clássico da Amizade"},
	{"fluminense-rj", "botafogo-rj", "Clássico Vovô"},
	{"fluminense-rj", "vasco-da-gama-rj", "Clássico dos Gigantes"},
	{"corinthians-sp", "palmeiras-sp", "Derby Paulista"},
	{"corinthians-sp", "sao-paulo-sp", "Majestoso"},
	{"corinthians-sp", "santos-sp", "Clássico Alvinegro"},
	{"palmeiras-sp", "sao-paulo-sp", "Choque-Rei"},
	{"palmeiras-sp", "santos-sp", "Clássico da Saudade"},
	{"sao-paulo-sp", "santos-sp", "San-São"},
	{"gremio-rs", "internacional-rs", "Gre-Nal"},
	{"atletico-mg", "cruzeiro-mg", "Clássico Mineiro"},
	{"atletico-pr", "coritiba-pr", "Atletiba"},
	{"bahia-ba", "vitoria-ba", "Ba-Vi"},
	{"sport-pe", "nautico-pe", "Clássico dos Clássicos"},
	{"sport-pe", "santa-cruz-pe", "Clássico das Multidões"},
	{"nautico-pe", "santa-cruz-pe", "Clássico dos Maiores"},
	{"ceara-ce", "fortaleza-ce", "Clássico-Rei"},
	{"goias-go", "vila-nova-go", "Clássico Goianiense"},
	{"avai-sc", "figueirense-sc", "Clássico da Capital"},
}
