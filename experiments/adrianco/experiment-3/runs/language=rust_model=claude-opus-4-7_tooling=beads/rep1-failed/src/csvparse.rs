//! Minimal CSV reader.
//!
//! Context: the provided Kaggle files mix quoting styles, embedded commas and
//! a UTF-8 BOM (`fifa_data.csv`). Rather than pull in a CSV crate we implement
//! a small RFC-4180 parser here. It tolerates `\r\n` / `\n` line endings,
//! doubled-quote escaping (`""`), quoted fields containing commas/newlines and
//! strips a leading byte-order mark.

/// Parse CSV `content` into a vector of records, each a vector of field
/// strings. The header row, if any, is the first returned record.
pub fn parse(content: &str) -> Vec<Vec<String>> {
    let mut rows: Vec<Vec<String>> = Vec::new();
    let mut record: Vec<String> = Vec::new();
    let mut field = String::new();
    let mut in_quotes = false;
    let mut chars = content.chars().peekable();

    // Strip a leading UTF-8 BOM if present.
    if chars.peek() == Some(&'\u{feff}') {
        chars.next();
    }

    while let Some(c) = chars.next() {
        if in_quotes {
            if c == '"' {
                if chars.peek() == Some(&'"') {
                    chars.next();
                    field.push('"');
                } else {
                    in_quotes = false;
                }
            } else {
                field.push(c);
            }
        } else {
            match c {
                '"' => in_quotes = true,
                ',' => record.push(std::mem::take(&mut field)),
                '\r' => {}
                '\n' => {
                    record.push(std::mem::take(&mut field));
                    rows.push(std::mem::take(&mut record));
                }
                _ => field.push(c),
            }
        }
    }

    // Flush a trailing record that was not newline-terminated.
    if !field.is_empty() || !record.is_empty() {
        record.push(field);
        rows.push(record);
    }
    rows
}

/// Build a case-insensitive `column-name -> index` lookup from a header row.
pub fn header_index(header: &[String]) -> std::collections::HashMap<String, usize> {
    header
        .iter()
        .enumerate()
        .map(|(i, name)| (name.trim().to_lowercase(), i))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_quoted_fields_with_commas() {
        let rows = parse("a,b\n\"x,y\",\"z\"\n");
        assert_eq!(rows.len(), 2);
        assert_eq!(rows[1], vec!["x,y".to_string(), "z".to_string()]);
    }

    #[test]
    fn strips_bom_and_handles_doubled_quotes() {
        let rows = parse("\u{feff}h\n\"a\"\"b\"");
        assert_eq!(rows[0], vec!["h".to_string()]);
        assert_eq!(rows[1], vec!["a\"b".to_string()]);
    }
}
