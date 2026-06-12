//! Canonical team-name resolution.
//!
//! The datasets spell the same club many ways: with a state suffix
//! ("Palmeiras-SP"), without one ("Palmeiras"), with the full club name
//! ("Atletico Mineiro") or with different accenting ("Gremio" / "Grêmio").
//! Worse, naive suffix-stripping *merges distinct clubs* — "Atlético-MG" and
//! "Athletico-PR" would both collapse to "atletico".
//!
//! This module maps every known Brazilian-league spelling onto one canonical
//! club identity via a curated alias table, so the same club is counted once
//! across every source file and distinct same-named clubs stay separate.
//! Names not in the table (e.g. foreign Libertadores clubs) fall back to a
//! suffix-preserving normal form, which keeps them distinct without merging.

use std::collections::HashMap;
use std::sync::OnceLock;

use crate::normalize::{display_team, fold};

/// Normal form used as the alias-table key and the fallback identity:
/// accents folded, parentheticals removed, hyphens treated as spaces.
fn norm_form(raw: &str) -> String {
    let mut no_parens = String::with_capacity(raw.len());
    let mut depth = 0i32;
    for c in raw.chars() {
        match c {
            '(' => depth += 1,
            ')' => {
                if depth > 0 {
                    depth -= 1
                }
            }
            '-' if depth == 0 => no_parens.push(' '),
            _ if depth == 0 => no_parens.push(c),
            _ => {}
        }
    }
    fold(&no_parens)
}

/// Curated alias groups: (canonical display name, [raw spellings seen in data]).
fn alias_groups() -> Vec<(&'static str, &'static [&'static str])> {
    vec![
        ("ABC", &["ABC"]),
        ("Confiança", &["AD Confianca", "Confianca", "Confianca SE"]),
        ("Altos", &["AE Altos", "Altos"]),
        ("Águia de Marabá", &["Aguia de Maraba"]),
        ("Amazonas", &["Amazonas"]),
        ("América-RN", &["America FC Natal", "America RN", "América-RN"]),
        ("América-MG", &["America MG", "America-MG", "América-MG"]),
        ("Aparecidense", &["Aparecidense", "Aparecidense GO"]),
        ("ASA", &["ASA", "ASA AL"]),
        (
            "Athletico-PR",
            &["Athletico Paranaense", "Athletico-PR", "Atletico Paranaense", "Atletico-PR"],
        ),
        ("Atlético Acreano", &["Atletico Acreano"]),
        ("Atlético-GO", &["Atletico Goianiense", "Atletico-GO", "Atlético-GO"]),
        ("Atlético-MG", &["Atletico Mineiro", "Atletico-MG", "Atlético-MG"]),
        ("Avaí", &["Avai", "Avaí", "Avai-SC"]),
        ("Bahia", &["Bahia", "Bahia-BA", "EC Bahia"]),
        ("Barueri", &["Barueri"]),
        ("Boa", &["Boa"]),
        ("Botafogo-PB", &["Botafogo PB"]),
        ("Botafogo-RJ", &["Botafogo RJ", "Botafogo-RJ"]),
        ("Botafogo-SP", &["Botafogo SP"]),
        ("Red Bull Bragantino", &["Bragantino", "Red Bull Bragantino-SP"]),
        ("Brasil de Pelotas", &["Brasil de Pelotas"]),
        ("Brasília", &["Brasilia FC"]),
        ("Brasiliense", &["Brasiliense"]),
        ("Brusque", &["Brusque"]),
        ("CA Paraná", &["CA Parana"]),
        ("CA Taguatinga", &["CA Taguatinga"]),
        ("Campinense", &["Campinense Clube"]),
        ("Caxias", &["Caxias", "Caxias RS"]),
        ("Ceará", &["Ceara", "Ceará", "Ceara-CE"]),
        ("Chapecoense", &["Chapecoense", "Chapecoense-SC"]),
        ("Remo", &["Clube Do Remo", "Remo", "Remo PA"]),
        ("Corinthians", &["Corinthians", "Corinthians-SP"]),
        ("Coritiba", &["Coritiba", "Coritiba-PR"]),
        ("CRAC", &["CRAC"]),
        ("CRB", &["CRB"]),
        ("Criciúma", &["Criciuma", "Criciúma", "Criciuma-SC"]),
        ("Cruzeiro", &["Cruzeiro", "Cruzeiro-MG"]),
        ("CSA", &["CS Alagoano", "CSA", "Csa-AL"]),
        ("Cuiabá", &["Cuiaba", "Cuiaba MT", "Cuiaba-MT"]),
        ("Duque de Caxias", &["Duque de Caxias FC", "Duque De Caxias RJ"]),
        ("Juventude", &["EC Juventude", "Juventude", "Juventude-RS"]),
        ("Atlético Cearense", &["FC Atlético Cearense"]),
        ("Ferroviário", &["Ferroviario"]),
        ("Figueirense", &["Figueirense", "Figueirense-SC"]),
        ("Flamengo", &["Flamengo", "Flamengo-RJ"]),
        ("Floresta", &["Floresta", "Floresta EC"]),
        ("Fluminense", &["Fluminense", "Fluminense-RJ"]),
        ("Fortaleza", &["Fortaleza", "Fortaleza EC", "Fortaleza FC", "Fortaleza-CE"]),
        ("GE Bagé", &["GE Bage"]),
        ("Globo", &["Globo FC"]),
        ("Goiás", &["Goias", "Goiás", "Goias-GO"]),
        ("Grêmio", &["Gremio", "Grêmio", "Gremio-RS"]),
        ("Novorizontino", &["Gremio Novorizontino", "Novorizontino"]),
        ("Grêmio Prudente", &["Grêmio Prudente"]),
        ("Guarani", &["Guarani", "Guarani SP", "Guarani-SP"]),
        ("Guaratinguetá", &["Guaratingueta"]),
        ("Grêmio Barueri", &["Guarulhos SP"]),
        ("Icasa", &["Icasa"]),
        ("Imperatriz", &["Imperatriz"]),
        ("Internacional", &["Internacional", "Internacional-RS"]),
        ("Ipatinga", &["Ipatinga"]),
        ("Ituano", &["Ituano"]),
        ("Jacuipense", &["Jacuipense"]),
        ("Joinville", &["Joinville", "Joinville-SC"]),
        ("Juazeirense", &["Juazeirense"]),
        ("Londrina", &["Londrina"]),
        ("Luverdense", &["Luverdense"]),
        ("Macaé", &["Macae Esporte FC", "Macae Esporte RJ"]),
        ("Madureira", &["Madureira EC", "Madureira RJ"]),
        ("Manaus", &["Manaus"]),
        ("Mirassol", &["Mirassol"]),
        ("Mogi Mirim", &["Mogi Mirim"]),
        ("Monsoon", &["Monsoon FC"]),
        ("Moto Club", &["Moto Club de São Luís", "Moto Clube"]),
        ("Náutico", &["Náutico", "Nautico Capibaribe", "Nautico-PE"]),
        ("Oeste", &["Oeste"]),
        ("Operário-PR", &["Operario PR"]),
        ("Palmeiras", &["Palmeiras", "Palmeiras-SP"]),
        ("Paraná", &["Parana", "Paraná", "Parana-PR"]),
        ("Paysandu", &["Paysandu"]),
        ("Ponte Preta", &["Ponte Preta", "Ponte Preta-SP"]),
        ("Portuguesa", &["Portuguesa", "Portuguesa Desportos", "Portuguesa-SP"]),
        ("Pouso Alegre", &["Pouso Alegre"]),
        ("River-PI", &["River AC"]),
        ("Salgueiro", &["Salgueiro"]),
        ("Sampaio Corrêa", &["Sampaio Correa"]),
        ("Santa Cruz", &["Santa Cruz", "Santa Cruz FC", "Santa Cruz-PE"]),
        ("Santo André", &["Santo André"]),
        ("Santos", &["Santos", "Santos-SP"]),
        ("São Bento", &["Sao Bento"]),
        ("São Bernardo", &["Sao Bernardo"]),
        ("São Caetano", &["Sao Caetano", "São Caetano"]),
        ("São José-PA", &["Sao Jose PA"]),
        ("São José-RS", &["Sao Jose RS"]),
        ("São Paulo", &["Sao Paulo", "São Paulo", "Sao Paulo-SP"]),
        ("Sport", &["Sport", "Sport Recife", "Sport-PE"]),
        ("Suzano", &["Suzano SP"]),
        ("Tombense", &["Tombense", "Tombense MG"]),
        ("Treze", &["Treze"]),
        ("Tupi", &["Tupi", "Tupi MG"]),
        ("Vasco", &["Vasco", "Vasco Da Gama RJ", "Vasco da Gama-RJ"]),
        ("Vila Nova", &["Vila Nova"]),
        ("Villa Nova", &["Villa Nova"]),
        ("Vitória", &["Vitoria", "Vitória", "Vitoria-BA"]),
        ("Volta Redonda", &["Volta Redonda"]),
        ("Ypiranga", &["Ypiranga", "Ypiranga RS"]),
    ]
}

fn alias_map() -> &'static HashMap<String, &'static str> {
    static MAP: OnceLock<HashMap<String, &'static str>> = OnceLock::new();
    MAP.get_or_init(|| {
        let mut m = HashMap::new();
        for (canonical, variants) in alias_groups() {
            m.insert(norm_form(canonical), canonical);
            for v in variants {
                m.insert(norm_form(v), canonical);
            }
        }
        m
    })
}

/// Resolve a raw team name to its `(match_key, display_name)`.
///
/// The match key is the folded canonical name and is what de-duplication,
/// standings and queries compare on.
pub fn canonical(raw: &str) -> (String, String) {
    let nf = norm_form(raw);
    match alias_map().get(&nf) {
        Some(canon) => (fold(canon), (*canon).to_string()),
        None => {
            // Unknown club: keep the suffix-bearing normal form as the key so
            // distinct same-named clubs do not merge.
            let key = if nf.is_empty() { fold(raw) } else { nf };
            (key, display_team(raw))
        }
    }
}

/// The canonical match key for a raw team name.
pub fn key(raw: &str) -> String {
    canonical(raw).0
}

/// The canonical display name for a raw team name (e.g. "flamengo" -> "Flamengo").
pub fn display(raw: &str) -> String {
    canonical(raw).1
}

/// Does a user-supplied team query match a stored canonical key?
pub fn query_matches(query: &str, stored_key: &str) -> bool {
    let q = key(query);
    if q.is_empty() || stored_key.is_empty() {
        return false;
    }
    stored_key == q || stored_key.contains(&q) || q.contains(stored_key)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unifies_spelling_variants() {
        assert_eq!(key("Flamengo"), key("Flamengo-RJ"));
        assert_eq!(key("Gremio"), key("Grêmio-RS"));
        assert_eq!(key("Atletico Mineiro"), key("Atlético-MG"));
        assert_eq!(key("Sao Paulo"), key("São Paulo-SP"));
        assert_eq!(key("Vasco"), key("Vasco da Gama-RJ"));
    }

    #[test]
    fn keeps_distinct_clubs_apart() {
        // The classic trap: two different "Atlético" clubs in different states.
        assert_ne!(key("Atlético-MG"), key("Athletico-PR"));
        assert_ne!(key("Botafogo-RJ"), key("Botafogo SP"));
        assert_ne!(key("América-MG"), key("América-RN"));
    }

    #[test]
    fn query_matching_is_canonical() {
        assert!(query_matches("Flamengo", &key("Flamengo-RJ")));
        assert!(query_matches("São Paulo", &key("Sao Paulo")));
        assert!(!query_matches("Santos", &key("Flamengo")));
    }
}
