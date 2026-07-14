const BRAZILIAN_STATE_CODES: &[&str] = &[
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR",
    "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
];

/// Strips a trailing Brazilian state-abbreviation suffix (e.g. "Palmeiras-SP" -> "Palmeiras").
pub fn normalize_team_name(name: &str) -> String {
    let trimmed = name.trim();
    if let Some((prefix, suffix)) = trimmed.rsplit_once('-') {
        let suffix = suffix.trim();
        if BRAZILIAN_STATE_CODES.contains(&suffix.to_uppercase().as_str()) {
            return prefix.trim().to_string();
        }
    }
    trimmed.to_string()
}

fn strip_accents(input: &str) -> String {
    input
        .chars()
        .map(|c| match c {
            'á' | 'à' | 'â' | 'ã' | 'ä' => 'a',
            'Á' | 'À' | 'Â' | 'Ã' | 'Ä' => 'A',
            'é' | 'è' | 'ê' | 'ë' => 'e',
            'É' | 'È' | 'Ê' | 'Ë' => 'E',
            'í' | 'ì' | 'î' | 'ï' => 'i',
            'Í' | 'Ì' | 'Î' | 'Ï' => 'I',
            'ó' | 'ò' | 'ô' | 'õ' | 'ö' => 'o',
            'Ó' | 'Ò' | 'Ô' | 'Õ' | 'Ö' => 'O',
            'ú' | 'ù' | 'û' | 'ü' => 'u',
            'Ú' | 'Ù' | 'Û' | 'Ü' => 'U',
            'ç' => 'c',
            'Ç' => 'C',
            'ñ' => 'n',
            'Ñ' => 'N',
            other => other,
        })
        .collect()
}

/// A canonical key for matching team names across datasets: strips the state
/// suffix, strips accents, lowercases, and drops non-alphanumeric characters.
/// Known alternate spellings (e.g. "Athletico"/"Atletico") are folded together.
pub fn team_comparison_key(name: &str) -> String {
    let without_suffix = normalize_team_name(name);
    let ascii = strip_accents(&without_suffix).to_lowercase();
    let alnum: String = ascii.chars().filter(|c| c.is_alphanumeric()).collect();
    alnum.replace("athletico", "atletico")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn strips_hyphenated_state_suffix() {
        assert_eq!(normalize_team_name("Palmeiras-SP"), "Palmeiras");
    }

    #[test]
    fn strips_spaced_hyphen_state_suffix() {
        assert_eq!(normalize_team_name("América - MG"), "América");
    }

    #[test]
    fn leaves_names_without_state_suffix_unchanged() {
        assert_eq!(normalize_team_name("Flamengo"), "Flamengo");
    }

    #[test]
    fn leaves_hyphenated_names_that_are_not_state_codes_unchanged() {
        assert_eq!(
            normalize_team_name("Nacional (URU)"),
            "Nacional (URU)"
        );
    }

    #[test]
    fn comparison_key_is_accent_and_case_insensitive() {
        assert_eq!(team_comparison_key("São Paulo"), team_comparison_key("Sao Paulo"));
        assert_eq!(team_comparison_key("Grêmio"), team_comparison_key("gremio"));
    }

    #[test]
    fn comparison_key_ignores_state_suffix_and_punctuation() {
        assert_eq!(
            team_comparison_key("Flamengo-RJ"),
            team_comparison_key("Flamengo")
        );
    }

    #[test]
    fn comparison_key_treats_athletico_and_atletico_pr_the_same() {
        // Both spellings refer to Athletico Paranaense in the datasets.
        assert_eq!(
            team_comparison_key("Athletico-PR"),
            team_comparison_key("Atletico-PR")
        );
    }

    #[test]
    fn strips_space_separated_state_suffix() {
        // BR-Football-Dataset.csv uses "Team STATE" without a hyphen.
        assert_eq!(normalize_team_name("Botafogo RJ"), "Botafogo");
    }

    #[test]
    fn comparison_key_folds_br_football_dataset_full_name_variants() {
        // These pairs name the same club across Brasileirao_Matches.csv,
        // novo_campeonato_brasileiro.csv, and BR-Football-Dataset.csv.
        let pairs = [
            ("Vasco Da Gama RJ", "Vasco"),
            ("Atletico Mineiro", "Atletico-MG"),
            ("Atletico Paranaense", "Atletico-PR"),
            ("EC Bahia", "Bahia"),
            ("Fortaleza FC", "Fortaleza"),
            ("Santa Cruz FC", "Santa Cruz-PE"),
            ("Atletico Goianiense", "Atletico-GO"),
        ];
        for (variant, canonical) in pairs {
            assert_eq!(
                team_comparison_key(variant),
                team_comparison_key(canonical),
                "{variant} should match {canonical}"
            );
        }
    }
}
