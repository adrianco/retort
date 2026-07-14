pub fn normalize_team_name(name: &str) -> String {
    // Remove state suffix patterns like -SP, -RJ, -MG, etc.
    let states = [
        "SP", "RJ", "MG", "RS", "PR", "RN", "SC", "CE", "PE", "GO", "BA", "ES", "PA", "PI",
        "AM", "MS", "MT", "RO", "AC", "RR", "AP", "TO", "AL", "SE", "PB", "MA", "DF",
    ];
    let mut result = name.trim().to_string();

    // Handle " - STATE" pattern used in Cup data (e.g., "Boavista Sport Club - RJ")
    for state in &states {
        let suffix = format!(" - {}", state);
        if result.ends_with(&suffix) {
            result = result[..result.len() - suffix.len()].to_string();
            break;
        }
    }

    // Remove state suffix patterns like -SP, -RJ, -MG, etc.
    for state in &states {
        let suffix = format!("-{}", state);
        if result.ends_with(&suffix) {
            result = result[..result.len() - suffix.len()].to_string();
            break;
        }
    }

    result.trim().to_string()
}

pub fn teams_match(name1: &str, name2: &str) -> bool {
    let n1 = normalize_team_name(name1).to_lowercase();
    let n2 = normalize_team_name(name2).to_lowercase();
    n1.contains(&n2) || n2.contains(&n1)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_normalize() {
        assert_eq!(normalize_team_name("Flamengo-RJ"), "Flamengo");
        assert_eq!(normalize_team_name("Palmeiras-SP"), "Palmeiras");
        assert_eq!(normalize_team_name("Boavista Sport Club - RJ"), "Boavista Sport Club");
        assert_eq!(normalize_team_name("Flamengo"), "Flamengo");
    }

    #[test]
    fn test_teams_match() {
        assert!(teams_match("Flamengo-RJ", "Flamengo"));
        assert!(teams_match("Palmeiras-SP", "Palmeiras"));
        assert!(!teams_match("Flamengo", "Fluminense"));
    }
}
