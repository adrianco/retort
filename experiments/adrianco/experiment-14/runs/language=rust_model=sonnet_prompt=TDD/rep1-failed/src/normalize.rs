pub fn normalize_team_name(name: &str) -> String {
    let name = name.trim();
    // Strip state suffix like "-SP", "-RJ", "-PR", etc.
    let name = strip_state_suffix(name);
    // Strip " - XX" suffix (cup format e.g. "América - MG")
    let name = strip_spaced_state_suffix(&name);
    name.trim().to_string()
}

fn strip_state_suffix(name: &str) -> String {
    // Match "-XX" at end where XX is 2 uppercase letters (Brazilian state codes)
    if let Some(idx) = name.rfind('-') {
        let suffix = &name[idx + 1..];
        if suffix.len() == 2 && suffix.chars().all(|c| c.is_ascii_uppercase()) {
            return name[..idx].trim().to_string();
        }
    }
    name.to_string()
}

fn strip_spaced_state_suffix(name: &str) -> String {
    // Match " - XX" at end where XX is 2 uppercase letters
    if name.len() >= 5 {
        let len = name.len();
        let tail = &name[len.saturating_sub(5)..];
        if tail.starts_with(" - ") {
            let code = &tail[3..];
            if code.len() == 2 && code.chars().all(|c| c.is_ascii_uppercase()) {
                return name[..len - 5].trim().to_string();
            }
        }
    }
    name.to_string()
}

pub fn teams_match(a: &str, b: &str) -> bool {
    let na = normalize_team_name(a).to_lowercase();
    let nb = normalize_team_name(b).to_lowercase();
    na == nb || na.contains(&nb) || nb.contains(&na)
}

pub fn team_contains(team: &str, query: &str) -> bool {
    let team_normalized = normalize_team_name(team).to_lowercase();
    let query_normalized = normalize_team_name(query).to_lowercase();
    team_normalized.contains(&query_normalized)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn strips_state_suffix() {
        assert_eq!(normalize_team_name("Palmeiras-SP"), "Palmeiras");
        assert_eq!(normalize_team_name("Flamengo-RJ"), "Flamengo");
        assert_eq!(normalize_team_name("Sport-PE"), "Sport");
        assert_eq!(normalize_team_name("Athletico-PR"), "Athletico");
    }

    #[test]
    fn strips_spaced_state_suffix() {
        assert_eq!(normalize_team_name("América - MG"), "América");
        assert_eq!(normalize_team_name("Botafogo - RJ"), "Botafogo");
    }

    #[test]
    fn leaves_plain_names_unchanged() {
        assert_eq!(normalize_team_name("Flamengo"), "Flamengo");
        assert_eq!(normalize_team_name("Palmeiras"), "Palmeiras");
        assert_eq!(normalize_team_name("Santos"), "Santos");
    }

    #[test]
    fn trims_whitespace() {
        assert_eq!(normalize_team_name("  Corinthians  "), "Corinthians");
    }

    #[test]
    fn handles_utf8_names() {
        assert_eq!(normalize_team_name("Grêmio-RS"), "Grêmio");
        assert_eq!(normalize_team_name("São Paulo-SP"), "São Paulo");
    }

    #[test]
    fn teams_match_with_suffix() {
        assert!(teams_match("Flamengo-RJ", "Flamengo"));
        assert!(teams_match("Palmeiras-SP", "Palmeiras-SP"));
        assert!(teams_match("São Paulo-SP", "São Paulo"));
    }

    #[test]
    fn team_contains_query() {
        assert!(team_contains("Flamengo-RJ", "Flamengo"));
        assert!(team_contains("Palmeiras-SP", "Palme"));
        assert!(!team_contains("Flamengo-RJ", "Palmeiras"));
    }

    #[test]
    fn does_not_strip_hyphenated_non_state() {
        // "Athletico-PR" should strip (PR is valid state)
        // "Nacional (URU)" should not be affected by state stripping
        assert_eq!(normalize_team_name("Nacional (URU)"), "Nacional (URU)");
    }
}
