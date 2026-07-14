//! Normalization helpers for the messy real-world data.
//!
//! The datasets name the same club many ways ("Palmeiras-SP", "Palmeiras",
//! "Nacional (URU)", "América - MG") and the same date three ways
//! ("2012-05-19 18:30:00", "2023-09-24", "29/03/2003"). These helpers fold
//! those variations onto a single canonical form so queries match consistently.

/// Fold a single character to its unaccented ASCII-ish equivalent (lowercased).
fn fold_char(c: char) -> char {
    match c {
        'á' | 'à' | 'â' | 'ã' | 'ä' | 'å' | 'Á' | 'À' | 'Â' | 'Ã' | 'Ä' | 'Å' => 'a',
        'é' | 'è' | 'ê' | 'ë' | 'É' | 'È' | 'Ê' | 'Ë' => 'e',
        'í' | 'ì' | 'î' | 'ï' | 'Í' | 'Ì' | 'Î' | 'Ï' => 'i',
        'ó' | 'ò' | 'ô' | 'õ' | 'ö' | 'Ó' | 'Ò' | 'Ô' | 'Õ' | 'Ö' => 'o',
        'ú' | 'ù' | 'û' | 'ü' | 'Ú' | 'Ù' | 'Û' | 'Ü' => 'u',
        'ç' | 'Ç' => 'c',
        'ñ' | 'Ñ' => 'n',
        other => other.to_ascii_lowercase(),
    }
}

/// Lower-case and strip accents; collapse whitespace.
pub fn fold(s: &str) -> String {
    let folded: String = s.chars().map(fold_char).collect();
    folded.split_whitespace().collect::<Vec<_>>().join(" ")
}

/// Strip a trailing state/country code suffix and any parenthetical, keeping the
/// original accents and casing. "Palmeiras-SP" -> "Palmeiras",
/// "Nacional (URU)" -> "Nacional", "América - MG" -> "América".
pub fn display_team(raw: &str) -> String {
    // Remove parenthetical groups.
    let mut out = String::with_capacity(raw.len());
    let mut depth = 0i32;
    for c in raw.chars() {
        match c {
            '(' => depth += 1,
            ')' => {
                if depth > 0 {
                    depth -= 1
                }
            }
            _ if depth == 0 => out.push(c),
            _ => {}
        }
    }
    let mut name = out.split_whitespace().collect::<Vec<_>>().join(" ");

    // Drop a trailing short alphabetic code after the final '-' (a UF / country).
    if let Some(idx) = name.rfind('-') {
        let suffix = name[idx + 1..].trim();
        let is_code = !suffix.is_empty()
            && suffix.len() <= 3
            && suffix.chars().all(|c| c.is_alphabetic());
        if is_code {
            name = name[..idx].trim().to_string();
        }
    }
    name.trim().to_string()
}

/// Parse any of the dataset date formats into ISO `YYYY-MM-DD` plus the year.
pub fn parse_date(raw: &str) -> Option<(String, i32)> {
    let s = raw.trim();
    if s.is_empty() {
        return None;
    }
    if s.contains('/') {
        // Brazilian DD/MM/YYYY.
        let parts: Vec<&str> = s.split('/').collect();
        if parts.len() == 3 {
            let d: u32 = parts[0].trim().parse().ok()?;
            let m: u32 = parts[1].trim().parse().ok()?;
            let y: i32 = parts[2].trim().get(0..4).unwrap_or(parts[2].trim()).parse().ok()?;
            return Some((format!("{y:04}-{m:02}-{d:02}"), y));
        }
        return None;
    }
    // ISO, optionally with a trailing time component.
    let date_part = s.split([' ', 'T']).next().unwrap_or(s);
    let bits: Vec<&str> = date_part.split('-').collect();
    if bits.len() >= 3 {
        let y: i32 = bits[0].parse().ok()?;
        let m: u32 = bits[1].parse().ok()?;
        let d: u32 = bits[2].parse().ok()?;
        return Some((format!("{y:04}-{m:02}-{d:02}"), y));
    }
    None
}

/// Map a free-form competition query onto one of the canonical names.
pub fn canonical_competition_query(query: &str) -> Option<&'static str> {
    let q = fold(query);
    if q.contains("serie b") || q.contains("série b") {
        Some("Brasileirão Série B")
    } else if q.contains("serie c") {
        Some("Brasileirão Série C")
    } else if q.contains("copa do brasil") || q == "cup" {
        Some("Copa do Brasil")
    } else if q.contains("libertadores") {
        Some("Copa Libertadores")
    } else if q.contains("brasileirao")
        || q.contains("serie a")
        || q.contains("brasileiro")
        || q.contains("brazilian league")
    {
        Some("Brasileirão")
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn strips_state_suffixes() {
        assert_eq!(display_team("Palmeiras-SP"), "Palmeiras");
        assert_eq!(display_team("América - MG"), "América");
        assert_eq!(display_team("Nacional (URU)"), "Nacional");
        assert_eq!(display_team("Barcelona-EQU"), "Barcelona");
        assert_eq!(
            display_team("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"),
            "Boavista Sport Club"
        );
        assert_eq!(
            display_team("Sport Club Corinthians Paulista"),
            "Sport Club Corinthians Paulista"
        );
    }

    #[test]
    fn dates() {
        assert_eq!(parse_date("2012-05-19 18:30:00"), Some(("2012-05-19".into(), 2012)));
        assert_eq!(parse_date("2023-09-24"), Some(("2023-09-24".into(), 2023)));
        assert_eq!(parse_date("29/03/2003"), Some(("2003-03-29".into(), 2003)));
    }

    #[test]
    fn competition_queries() {
        assert_eq!(canonical_competition_query("Brasileirão"), Some("Brasileirão"));
        assert_eq!(canonical_competition_query("serie a"), Some("Brasileirão"));
        assert_eq!(canonical_competition_query("Copa do Brasil"), Some("Copa do Brasil"));
        assert_eq!(canonical_competition_query("libertadores"), Some("Copa Libertadores"));
        assert_eq!(canonical_competition_query("Serie B"), Some("Brasileirão Série B"));
    }
}
