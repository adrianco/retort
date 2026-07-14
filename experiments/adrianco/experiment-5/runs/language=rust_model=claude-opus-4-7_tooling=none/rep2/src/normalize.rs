//! Team name and date normalization helpers.

/// Lowercase, strip accents, drop punctuation, collapse whitespace, and
/// remove common suffixes/prefixes so equivalent team names compare equal.
pub fn normalize_team(name: &str) -> String {
    let mut s = strip_accents(name).to_lowercase();

    if let Some(idx) = s.rfind(" -") {
        let tail = &s[idx + 2..].trim();
        if is_state_or_country_code(tail) {
            s.truncate(idx);
        }
    }
    if let Some(idx) = s.rfind('-') {
        let tail = s[idx + 1..].trim();
        if is_state_or_country_code(tail) {
            s.truncate(idx);
        }
    }
    if let Some(idx) = s.rfind('(') {
        if let Some(end) = s.rfind(')') {
            if end > idx {
                let inside = s[idx + 1..end].trim();
                if is_state_or_country_code(inside) {
                    s.replace_range(idx..=end, "");
                }
            }
        }
    }

    let cleaned: String = s
        .chars()
        .map(|c| if c.is_alphanumeric() || c.is_whitespace() { c } else { ' ' })
        .collect();
    let filler: &[&str] = &[
        "futebol clube",
        "sport club",
        "esporte clube",
        "clube de regatas",
        "esporte",
        "futebol",
        "fc",
        "ec",
        "sc",
    ];
    let tokens: Vec<&str> = cleaned.split_whitespace().collect();
    let mut out = Vec::with_capacity(tokens.len());
    let mut i = 0;
    while i < tokens.len() {
        let mut matched = false;
        for f in filler {
            let fw: Vec<&str> = f.split_whitespace().collect();
            if i + fw.len() <= tokens.len() && tokens[i..i + fw.len()] == fw[..] {
                i += fw.len();
                matched = true;
                break;
            }
        }
        if !matched {
            out.push(tokens[i]);
            i += 1;
        }
    }
    out.join(" ")
}

fn is_state_or_country_code(s: &str) -> bool {
    let s = s.trim();
    !s.is_empty()
        && s.len() <= 5
        && s.chars().all(|c| c.is_ascii_alphabetic())
}

/// Map a small set of common Latin Portuguese characters to ASCII.
pub fn strip_accents(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for c in s.chars() {
        let replacement = match c {
            'á' | 'à' | 'ã' | 'â' | 'ä' => 'a',
            'Á' | 'À' | 'Ã' | 'Â' | 'Ä' => 'A',
            'é' | 'è' | 'ê' | 'ë' => 'e',
            'É' | 'È' | 'Ê' | 'Ë' => 'E',
            'í' | 'ì' | 'î' | 'ï' => 'i',
            'Í' | 'Ì' | 'Î' | 'Ï' => 'I',
            'ó' | 'ò' | 'õ' | 'ô' | 'ö' => 'o',
            'Ó' | 'Ò' | 'Õ' | 'Ô' | 'Ö' => 'O',
            'ú' | 'ù' | 'û' | 'ü' => 'u',
            'Ú' | 'Ù' | 'Û' | 'Ü' => 'U',
            'ç' => 'c',
            'Ç' => 'C',
            'ñ' => 'n',
            'Ñ' => 'N',
            other => {
                out.push(other);
                continue;
            }
        };
        out.push(replacement);
    }
    out
}

/// Returns true if `query` matches `name` after normalization. Supports both
/// exact and substring matching.
pub fn team_matches(name: &str, query: &str) -> bool {
    if name.is_empty() || query.is_empty() {
        return false;
    }
    let n = normalize_team(name);
    let q = normalize_team(query);
    if q.is_empty() {
        return false;
    }
    n == q || n.contains(&q)
}

/// Parse a date string in any of the supported formats. Returns `(year, month, day)`.
pub fn parse_date(raw: &str) -> Option<(i32, u32, u32)> {
    let raw = raw.trim();
    if raw.is_empty() {
        return None;
    }

    let main = raw.split_whitespace().next().unwrap_or(raw);

    if let Some((y, m, d)) = parse_iso(main) {
        return Some((y, m, d));
    }
    if let Some((y, m, d)) = parse_brazilian(main) {
        return Some((y, m, d));
    }
    None
}

fn parse_iso(s: &str) -> Option<(i32, u32, u32)> {
    let parts: Vec<&str> = s.split('-').collect();
    if parts.len() != 3 {
        return None;
    }
    let year: i32 = parts[0].parse().ok()?;
    let month: u32 = parts[1].parse().ok()?;
    let day: u32 = parts[2].parse().ok()?;
    if month == 0 || month > 12 || day == 0 || day > 31 {
        return None;
    }
    Some((year, month, day))
}

fn parse_brazilian(s: &str) -> Option<(i32, u32, u32)> {
    let parts: Vec<&str> = s.split('/').collect();
    if parts.len() != 3 {
        return None;
    }
    let day: u32 = parts[0].parse().ok()?;
    let month: u32 = parts[1].parse().ok()?;
    let year: i32 = parts[2].parse().ok()?;
    if month == 0 || month > 12 || day == 0 || day > 31 {
        return None;
    }
    Some((year, month, day))
}

/// Render a parsed date as ISO `YYYY-MM-DD`.
pub fn format_iso(y: i32, m: u32, d: u32) -> String {
    format!("{:04}-{:02}-{:02}", y, m, d)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalize_drops_state_suffix() {
        assert_eq!(normalize_team("Palmeiras-SP"), normalize_team("Palmeiras"));
        assert_eq!(normalize_team("Flamengo-RJ"), normalize_team("Flamengo"));
    }

    #[test]
    fn normalize_handles_accents() {
        assert_eq!(normalize_team("São Paulo"), normalize_team("Sao Paulo"));
        assert_eq!(normalize_team("Grêmio"), normalize_team("Gremio"));
    }

    #[test]
    fn normalize_handles_country_suffix() {
        let a = normalize_team("Nacional (URU)");
        let b = normalize_team("Nacional");
        assert_eq!(a, b);
    }

    #[test]
    fn normalize_drops_filler() {
        assert_eq!(
            normalize_team("Sport Club Corinthians Paulista"),
            normalize_team("Corinthians Paulista")
        );
    }

    #[test]
    fn team_matches_substring() {
        assert!(team_matches("Sport Club Corinthians Paulista", "Corinthians"));
        assert!(team_matches("Flamengo-RJ", "flamengo"));
    }

    #[test]
    fn parse_dates() {
        assert_eq!(parse_date("2023-09-24"), Some((2023, 9, 24)));
        assert_eq!(parse_date("29/03/2003"), Some((2003, 3, 29)));
        assert_eq!(parse_date("2012-05-19 18:30:00"), Some((2012, 5, 19)));
        assert_eq!(parse_date(""), None);
    }
}
