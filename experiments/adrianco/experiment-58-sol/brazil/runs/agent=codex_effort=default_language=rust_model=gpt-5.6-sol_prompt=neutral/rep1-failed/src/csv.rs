use std::{collections::HashMap, fs, io, path::Path};

#[derive(Debug, Clone)]
pub struct CsvTable {
    headers: Vec<String>,
    rows: Vec<Vec<String>>,
}

impl CsvTable {
    pub fn from_path(path: &Path) -> io::Result<Self> {
        let text = fs::read_to_string(path)?;
        Self::parse(&text).map_err(|message| io::Error::new(io::ErrorKind::InvalidData, message))
    }

    pub fn parse(text: &str) -> Result<Self, String> {
        let mut records = parse_records(text)?;
        if records.is_empty() {
            return Err("CSV has no header row".into());
        }
        let mut headers = records.remove(0);
        if let Some(first) = headers.first_mut() {
            *first = first.trim_start_matches('\u{feff}').to_string();
        }
        Ok(Self {
            headers,
            rows: records,
        })
    }

    pub fn len(&self) -> usize {
        self.rows.len()
    }

    pub fn is_empty(&self) -> bool {
        self.rows.is_empty()
    }

    pub fn rows(&self) -> impl Iterator<Item = CsvRow<'_>> {
        self.rows.iter().map(|values| CsvRow {
            headers: &self.headers,
            values,
        })
    }

    pub fn headers(&self) -> &[String] {
        &self.headers
    }
}

#[derive(Clone, Copy)]
pub struct CsvRow<'a> {
    headers: &'a [String],
    values: &'a [String],
}

impl<'a> CsvRow<'a> {
    pub fn get(&self, name: &str) -> Option<&'a str> {
        self.headers
            .iter()
            .position(|header| header.eq_ignore_ascii_case(name))
            .and_then(|index| self.values.get(index))
            .map(String::as_str)
            .filter(|value| !value.trim().is_empty())
    }

    pub fn to_map(&self) -> HashMap<&'a str, &'a str> {
        self.headers
            .iter()
            .zip(self.values)
            .map(|(key, value)| (key.as_str(), value.as_str()))
            .collect()
    }
}

fn parse_records(text: &str) -> Result<Vec<Vec<String>>, String> {
    let mut records = Vec::new();
    let mut record = Vec::new();
    let mut field = String::new();
    let mut chars = text.chars().peekable();
    let mut quoted = false;

    while let Some(ch) = chars.next() {
        match ch {
            '"' if quoted && chars.peek() == Some(&'"') => {
                chars.next();
                field.push('"');
            }
            '"' => quoted = !quoted,
            ',' if !quoted => {
                record.push(std::mem::take(&mut field));
            }
            '\n' if !quoted => {
                if field.ends_with('\r') {
                    field.pop();
                }
                record.push(std::mem::take(&mut field));
                if record.iter().any(|value| !value.is_empty()) {
                    records.push(std::mem::take(&mut record));
                } else {
                    record.clear();
                }
            }
            _ => field.push(ch),
        }
    }
    if quoted {
        return Err("unterminated quoted CSV field".into());
    }
    if !field.is_empty() || !record.is_empty() {
        record.push(field.trim_end_matches('\r').to_string());
        records.push(record);
    }
    Ok(records)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_quotes_commas_bom_and_newlines() {
        let table = CsvTable::parse("\u{feff}name,note\r\nFlamengo,\"Rio, RJ\"\r\nA,\"line\n2\"\n")
            .unwrap();
        assert_eq!(table.headers(), &["name", "note"]);
        assert_eq!(table.len(), 2);
        let rows: Vec<_> = table.rows().collect();
        assert_eq!(rows[0].get("note"), Some("Rio, RJ"));
        assert_eq!(rows[1].get("note"), Some("line\n2"));
    }
}
