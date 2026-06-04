// =============================================================================
// normalize — team-name normalization and date parsing
// -----------------------------------------------------------------------------
// Context:
//   The provided datasets use inconsistent conventions (see the "Data Quality
//   Notes" section of TASK.md):
//     * Team names may carry a state suffix ("Palmeiras-SP", "América - MG"),
//       a parenthetical ("Nacional (URU)", "Boavista Sport Club (...) - RJ")
//       or accents ("São Paulo", "Grêmio", "Avaí").
//     * Dates appear as ISO ("2023-09-24"), ISO+time ("2012-05-19 18:30:00")
//       or Brazilian ("29/03/2003").
//
//   This module turns those into:
//     * a stable, accent-free, suffix-free *canonical key* used for matching,
//     * a clean human-readable *display name*,
//     * a normalized ISO date string plus an integer sort key.
// =============================================================================

/// Strip common Portuguese accents/diacritics, mapping each accented letter to
/// its ASCII base. Used only for building match keys — display names keep their
/// accents.
pub fn strip_accents(s: &str) -> String {
    s.chars()
        .map(|c| match c {
            'á' | 'à' | 'â' | 'ã' | 'ä' | 'å' => 'a',
            'é' | 'è' | 'ê' | 'ë' => 'e',
            'í' | 'ì' | 'î' | 'ï' => 'i',
            'ó' | 'ò' | 'ô' | 'õ' | 'ö' => 'o',
            'ú' | 'ù' | 'û' | 'ü' => 'u',
            'ç' => 'c',
            'ñ' => 'n',
            'Á' | 'À' | 'Â' | 'Ã' | 'Ä' | 'Å' => 'A',
            'É' | 'È' | 'Ê' | 'Ë' => 'E',
            'Í' | 'Ì' | 'Î' | 'Ï' => 'I',
            'Ó' | 'Ò' | 'Ô' | 'Õ' | 'Ö' => 'O',
            'Ú' | 'Ù' | 'Û' | 'Ü' => 'U',
            'Ç' => 'C',
            'Ñ' => 'N',
            other => other,
        })
        .collect()
}

/// Remove any parenthetical groups, e.g. "Nacional (URU)" -> "Nacional ".
fn remove_parens(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let mut depth = 0u32;
    for c in s.chars() {
        match c {
            '(' | '[' => depth += 1,
            ')' | ']' => {
                if depth > 0 {
                    depth -= 1;
                }
            }
            _ if depth == 0 => out.push(c),
            _ => {}
        }
    }
    out
}

/// Strip a trailing state/country suffix such as "-SP", " - MG" or " - RJ"
/// where the suffix after the final '-' is a short (2-3) alphabetic code.
fn strip_state_suffix(s: &str) -> String {
    let t = s.trim_end();
    if let Some(idx) = t.rfind('-') {
        let tail = t[idx + 1..].trim();
        let len = tail.chars().count();
        if (2..=3).contains(&len) && tail.chars().all(|c| c.is_ascii_alphabetic()) {
            return t[..idx].trim_end().to_string();
        }
    }
    t.to_string()
}

/// Collapse runs of whitespace into a single space and trim.
fn collapse_ws(s: &str) -> String {
    s.split_whitespace().collect::<Vec<_>>().join(" ")
}

/// Human-readable team name: parentheticals and state suffix removed, accents
/// kept. e.g. "Palmeiras-SP" -> "Palmeiras", "São Paulo" stays "São Paulo".
pub fn display_team(raw: &str) -> String {
    let no_parens = remove_parens(raw);
    let no_state = strip_state_suffix(&no_parens);
    let cleaned = collapse_ws(&no_state);
    if cleaned.is_empty() {
        collapse_ws(raw)
    } else {
        cleaned
    }
}

/// Canonical match key: lowercase, accent-free, suffix-free, alphanumeric words
/// joined by single spaces. Two names that refer to the same club should map to
/// the same key. e.g. "Palmeiras-SP", "Palmeiras (SP)" and "palmeiras" all map
/// to "palmeiras".
pub fn team_key(raw: &str) -> String {
    let display = display_team(raw);
    let ascii = strip_accents(&display).to_lowercase();
    let mut out = String::with_capacity(ascii.len());
    for c in ascii.chars() {
        if c.is_alphanumeric() {
            out.push(c);
        } else {
            out.push(' ');
        }
    }
    collapse_ws(&out)
}

/// Returns true if a stored team key matches a user-supplied query key, allowing
/// substring matches in either direction so "Sao Paulo" matches "Sao Paulo FC"
/// and vice-versa. Empty query never matches.
pub fn key_matches(stored_key: &str, query_key: &str) -> bool {
    if query_key.is_empty() || stored_key.is_empty() {
        return false;
    }
    stored_key == query_key
        || stored_key.contains(query_key)
        || query_key.contains(stored_key)
}

/// Parse a date in any of the supported formats into `(iso_string, sort_key)`.
/// `sort_key` is `year*10000 + month*100 + day` (0 when unparseable) so dates
/// sort chronologically as integers. The ISO string is "YYYY-MM-DD"; if parsing
/// fails the original (trimmed) text is returned with a 0 sort key.
pub fn parse_date(raw: &str) -> (String, i64) {
    let s = raw.trim();
    if s.is_empty() {
        return (String::new(), 0);
    }
    // Drop any time component ("2012-05-19 18:30:00" -> "2012-05-19").
    let date_part = s.split_whitespace().next().unwrap_or(s);

    if date_part.contains('/') {
        // Brazilian DD/MM/YYYY
        let p: Vec<&str> = date_part.split('/').collect();
        if p.len() == 3 {
            if let (Ok(d), Ok(m), Ok(y)) = (
                p[0].trim().parse::<i64>(),
                p[1].trim().parse::<i64>(),
                p[2].trim().parse::<i64>(),
            ) {
                if valid_ymd(y, m, d) {
                    return (format!("{:04}-{:02}-{:02}", y, m, d), y * 10000 + m * 100 + d);
                }
            }
        }
    } else if date_part.contains('-') {
        // ISO YYYY-MM-DD
        let p: Vec<&str> = date_part.split('-').collect();
        if p.len() == 3 {
            if let (Ok(y), Ok(m), Ok(d)) = (
                p[0].trim().parse::<i64>(),
                p[1].trim().parse::<i64>(),
                p[2].trim().parse::<i64>(),
            ) {
                if valid_ymd(y, m, d) {
                    return (format!("{:04}-{:02}-{:02}", y, m, d), y * 10000 + m * 100 + d);
                }
            }
        }
    }
    (s.to_string(), 0)
}

fn valid_ymd(y: i64, m: i64, d: i64) -> bool {
    y > 1800 && y < 3000 && (1..=12).contains(&m) && (1..=31).contains(&d)
}

/// Parse an integer that may be written as a float ("1", "1.0", "2") or be
/// empty/blank (returns None).
pub fn parse_int(s: &str) -> Option<i64> {
    let t = s.trim();
    if t.is_empty() {
        return None;
    }
    if let Ok(i) = t.parse::<i64>() {
        return Some(i);
    }
    if let Ok(f) = t.parse::<f64>() {
        if f.is_finite() {
            return Some(f.round() as i64);
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalizes_state_suffix() {
        assert_eq!(team_key("Palmeiras-SP"), "palmeiras");
        assert_eq!(team_key("Palmeiras"), "palmeiras");
        assert_eq!(team_key("América - MG"), "america");
        assert_eq!(display_team("Palmeiras-SP"), "Palmeiras");
    }

    #[test]
    fn normalizes_accents_and_parens() {
        assert_eq!(team_key("São Paulo"), "sao paulo");
        assert_eq!(team_key("Grêmio"), "gremio");
        assert_eq!(team_key("Nacional (URU)"), "nacional");
        assert_eq!(display_team("Nacional (URU)"), "Nacional");
    }

    #[test]
    fn flexible_matching() {
        assert!(key_matches(&team_key("São Paulo FC"), &team_key("Sao Paulo")));
        assert!(key_matches(&team_key("Flamengo-RJ"), &team_key("flamengo")));
        assert!(!key_matches(&team_key("Flamengo"), &team_key("Fluminense")));
    }

    #[test]
    fn parses_dates() {
        assert_eq!(parse_date("2023-09-24"), ("2023-09-24".to_string(), 20230924));
        assert_eq!(
            parse_date("2012-05-19 18:30:00"),
            ("2012-05-19".to_string(), 20120519)
        );
        assert_eq!(parse_date("29/03/2003"), ("2003-03-29".to_string(), 20030329));
    }

    #[test]
    fn parses_ints() {
        assert_eq!(parse_int("1"), Some(1));
        assert_eq!(parse_int("1.0"), Some(1));
        assert_eq!(parse_int(""), None);
        assert_eq!(parse_int("  3 "), Some(3));
    }
}
