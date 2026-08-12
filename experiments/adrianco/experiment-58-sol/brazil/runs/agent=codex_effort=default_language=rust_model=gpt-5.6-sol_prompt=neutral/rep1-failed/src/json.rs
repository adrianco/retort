use std::collections::BTreeMap;

#[derive(Debug, Clone, PartialEq)]
pub enum Json {
    Null,
    Bool(bool),
    Number(f64),
    String(String),
    Array(Vec<Json>),
    Object(BTreeMap<String, Json>),
}

impl Json {
    pub fn parse(input: &str) -> Result<Self, String> {
        let mut parser = Parser {
            bytes: input.as_bytes(),
            index: 0,
        };
        let value = parser.value()?;
        parser.whitespace();
        if parser.index != parser.bytes.len() {
            return Err(format!("unexpected trailing data at byte {}", parser.index));
        }
        Ok(value)
    }

    pub fn stringify(&self) -> String {
        let mut output = String::new();
        self.write_to(&mut output);
        output
    }

    pub fn get(&self, key: &str) -> Option<&Json> {
        match self {
            Json::Object(values) => values.get(key),
            _ => None,
        }
    }

    pub fn as_str(&self) -> Option<&str> {
        match self {
            Json::String(value) => Some(value),
            _ => None,
        }
    }

    pub fn as_i64(&self) -> Option<i64> {
        match self {
            Json::Number(value) if value.is_finite() => Some(*value as i64),
            _ => None,
        }
    }

    pub fn as_u64(&self) -> Option<u64> {
        self.as_i64().and_then(|value| value.try_into().ok())
    }

    pub fn as_bool(&self) -> Option<bool> {
        match self {
            Json::Bool(value) => Some(*value),
            _ => None,
        }
    }

    fn write_to(&self, output: &mut String) {
        match self {
            Json::Null => output.push_str("null"),
            Json::Bool(value) => output.push_str(if *value { "true" } else { "false" }),
            Json::Number(value) => {
                if value.is_finite() {
                    output.push_str(&value.to_string())
                } else {
                    output.push_str("null")
                }
            }
            Json::String(value) => write_string(value, output),
            Json::Array(values) => {
                output.push('[');
                for (index, value) in values.iter().enumerate() {
                    if index > 0 {
                        output.push(',');
                    }
                    value.write_to(output);
                }
                output.push(']');
            }
            Json::Object(values) => {
                output.push('{');
                for (index, (key, value)) in values.iter().enumerate() {
                    if index > 0 {
                        output.push(',');
                    }
                    write_string(key, output);
                    output.push(':');
                    value.write_to(output);
                }
                output.push('}');
            }
        }
    }
}

impl From<&str> for Json {
    fn from(value: &str) -> Self {
        Json::String(value.into())
    }
}
impl From<String> for Json {
    fn from(value: String) -> Self {
        Json::String(value)
    }
}
impl From<bool> for Json {
    fn from(value: bool) -> Self {
        Json::Bool(value)
    }
}
impl From<usize> for Json {
    fn from(value: usize) -> Self {
        Json::Number(value as f64)
    }
}
impl From<u32> for Json {
    fn from(value: u32) -> Self {
        Json::Number(value as f64)
    }
}
impl From<i32> for Json {
    fn from(value: i32) -> Self {
        Json::Number(value as f64)
    }
}
impl From<f64> for Json {
    fn from(value: f64) -> Self {
        Json::Number(value)
    }
}

pub fn object(entries: impl IntoIterator<Item = (impl Into<String>, Json)>) -> Json {
    Json::Object(
        entries
            .into_iter()
            .map(|(key, value)| (key.into(), value))
            .collect(),
    )
}

fn write_string(value: &str, output: &mut String) {
    output.push('"');
    for ch in value.chars() {
        match ch {
            '"' => output.push_str("\\\""),
            '\\' => output.push_str("\\\\"),
            '\n' => output.push_str("\\n"),
            '\r' => output.push_str("\\r"),
            '\t' => output.push_str("\\t"),
            '\u{08}' => output.push_str("\\b"),
            '\u{0c}' => output.push_str("\\f"),
            ch if ch < '\u{20}' => output.push_str(&format!("\\u{:04x}", ch as u32)),
            ch => output.push(ch),
        }
    }
    output.push('"');
}

struct Parser<'a> {
    bytes: &'a [u8],
    index: usize,
}

impl Parser<'_> {
    fn value(&mut self) -> Result<Json, String> {
        self.whitespace();
        match self.peek() {
            Some(b'n') => {
                self.literal(b"null")?;
                Ok(Json::Null)
            }
            Some(b't') => {
                self.literal(b"true")?;
                Ok(Json::Bool(true))
            }
            Some(b'f') => {
                self.literal(b"false")?;
                Ok(Json::Bool(false))
            }
            Some(b'"') => Ok(Json::String(self.string()?)),
            Some(b'[') => self.array(),
            Some(b'{') => self.object(),
            Some(b'-' | b'0'..=b'9') => self.number(),
            Some(byte) => Err(format!(
                "unexpected byte '{}' at {}",
                byte as char, self.index
            )),
            None => Err("unexpected end of JSON".into()),
        }
    }

    fn object(&mut self) -> Result<Json, String> {
        self.index += 1;
        let mut values = BTreeMap::new();
        self.whitespace();
        if self.take(b'}') {
            return Ok(Json::Object(values));
        }
        loop {
            self.whitespace();
            if self.peek() != Some(b'"') {
                return Err(format!("expected object key at {}", self.index));
            }
            let key = self.string()?;
            self.whitespace();
            if !self.take(b':') {
                return Err(format!("expected ':' at {}", self.index));
            }
            values.insert(key, self.value()?);
            self.whitespace();
            if self.take(b'}') {
                break;
            }
            if !self.take(b',') {
                return Err(format!("expected ',' at {}", self.index));
            }
        }
        Ok(Json::Object(values))
    }

    fn array(&mut self) -> Result<Json, String> {
        self.index += 1;
        let mut values = Vec::new();
        self.whitespace();
        if self.take(b']') {
            return Ok(Json::Array(values));
        }
        loop {
            values.push(self.value()?);
            self.whitespace();
            if self.take(b']') {
                break;
            }
            if !self.take(b',') {
                return Err(format!("expected ',' at {}", self.index));
            }
        }
        Ok(Json::Array(values))
    }

    fn string(&mut self) -> Result<String, String> {
        self.index += 1;
        let mut output = String::new();
        while let Some(byte) = self.peek() {
            self.index += 1;
            match byte {
                b'"' => return Ok(output),
                b'\\' => {
                    let escaped = self.peek().ok_or("incomplete JSON escape")?;
                    self.index += 1;
                    match escaped {
                        b'"' => output.push('"'),
                        b'\\' => output.push('\\'),
                        b'/' => output.push('/'),
                        b'b' => output.push('\u{08}'),
                        b'f' => output.push('\u{0c}'),
                        b'n' => output.push('\n'),
                        b'r' => output.push('\r'),
                        b't' => output.push('\t'),
                        b'u' => {
                            let first = self.hex4()?;
                            let code = if (0xd800..=0xdbff).contains(&first) {
                                if !self.take(b'\\') || !self.take(b'u') {
                                    return Err("missing low surrogate".into());
                                }
                                let low = self.hex4()?;
                                if !(0xdc00..=0xdfff).contains(&low) {
                                    return Err("invalid low surrogate".into());
                                }
                                0x10000 + (((first - 0xd800) as u32) << 10) + (low - 0xdc00) as u32
                            } else {
                                first as u32
                            };
                            output.push(char::from_u32(code).ok_or("invalid Unicode code point")?);
                        }
                        _ => return Err("invalid JSON escape".into()),
                    }
                }
                byte if byte < 0x20 => return Err("control byte in JSON string".into()),
                byte if byte < 0x80 => output.push(byte as char),
                _ => {
                    self.index -= 1;
                    let remainder = std::str::from_utf8(&self.bytes[self.index..])
                        .map_err(|_| "invalid UTF-8")?;
                    let ch = remainder.chars().next().unwrap();
                    output.push(ch);
                    self.index += ch.len_utf8();
                }
            }
        }
        Err("unterminated JSON string".into())
    }

    fn hex4(&mut self) -> Result<u16, String> {
        if self.index + 4 > self.bytes.len() {
            return Err("incomplete Unicode escape".into());
        }
        let text = std::str::from_utf8(&self.bytes[self.index..self.index + 4])
            .map_err(|_| "bad Unicode escape")?;
        self.index += 4;
        u16::from_str_radix(text, 16).map_err(|_| "bad Unicode escape".into())
    }

    fn number(&mut self) -> Result<Json, String> {
        let start = self.index;
        while matches!(
            self.peek(),
            Some(b'-' | b'+' | b'.' | b'e' | b'E' | b'0'..=b'9')
        ) {
            self.index += 1;
        }
        let text = std::str::from_utf8(&self.bytes[start..self.index]).unwrap();
        text.parse::<f64>()
            .map(Json::Number)
            .map_err(|_| format!("invalid number '{text}'"))
    }

    fn literal(&mut self, literal: &[u8]) -> Result<(), String> {
        if self.bytes.get(self.index..self.index + literal.len()) == Some(literal) {
            self.index += literal.len();
            Ok(())
        } else {
            Err(format!("invalid literal at {}", self.index))
        }
    }

    fn whitespace(&mut self) {
        while matches!(self.peek(), Some(b' ' | b'\n' | b'\r' | b'\t')) {
            self.index += 1;
        }
    }
    fn peek(&self) -> Option<u8> {
        self.bytes.get(self.index).copied()
    }
    fn take(&mut self, expected: u8) -> bool {
        if self.peek() == Some(expected) {
            self.index += 1;
            true
        } else {
            false
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn round_trips_nested_unicode_json() {
        let input = r#"{"a":[true,null,-2.5],"name":"São \ud83c\uddeb\ud83c\uddf7"}"#;
        let parsed = Json::parse(input).unwrap();
        let reparsed = Json::parse(&parsed.stringify()).unwrap();
        assert_eq!(parsed, reparsed);
        assert_eq!(parsed.get("name").and_then(Json::as_str), Some("São 🇫🇷"));
    }
}
