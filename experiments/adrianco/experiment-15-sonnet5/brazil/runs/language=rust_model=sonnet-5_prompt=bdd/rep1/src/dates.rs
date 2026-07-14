//! Flexible date parsing for the mixed formats used across datasets:
//! ISO with time ("2012-05-19 18:30:00"), ISO date-only ("2023-09-24"),
//! and Brazilian day/month/year ("29/03/2003").

use chrono::NaiveDate;

/// Parse a date string in any of the supported formats. Returns `None` for
/// blank or unrecognized input rather than failing the whole row load.
pub fn parse_flexible_date(raw: &str) -> Option<NaiveDate> {
    let raw = raw.trim();
    if raw.is_empty() {
        return None;
    }
    if let Ok(dt) = chrono::NaiveDateTime::parse_from_str(raw, "%Y-%m-%d %H:%M:%S") {
        return Some(dt.date());
    }
    if let Ok(d) = NaiveDate::parse_from_str(raw, "%Y-%m-%d") {
        return Some(d);
    }
    if let Ok(d) = NaiveDate::parse_from_str(raw, "%d/%m/%Y") {
        return Some(d);
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    // Given an ISO datetime string
    // When parsing it
    // Then the date component is extracted
    #[test]
    fn test_given_iso_datetime_when_parsing_then_date_is_extracted() {
        assert_eq!(
            parse_flexible_date("2012-05-19 18:30:00"),
            NaiveDate::from_ymd_opt(2012, 5, 19)
        );
    }

    // Given an ISO date-only string
    // When parsing it
    // Then the date is extracted directly
    #[test]
    fn test_given_iso_date_only_when_parsing_then_date_is_extracted() {
        assert_eq!(
            parse_flexible_date("2023-09-24"),
            NaiveDate::from_ymd_opt(2023, 9, 24)
        );
    }

    // Given a Brazilian day/month/year string
    // When parsing it
    // Then the date is extracted with fields in the right order
    #[test]
    fn test_given_brazilian_date_format_when_parsing_then_date_is_extracted() {
        assert_eq!(
            parse_flexible_date("29/03/2003"),
            NaiveDate::from_ymd_opt(2003, 3, 29)
        );
    }

    // Given a blank string
    // When parsing it
    // Then no date is returned
    #[test]
    fn test_given_blank_string_when_parsing_then_none_is_returned() {
        assert_eq!(parse_flexible_date(""), None);
        assert_eq!(parse_flexible_date("   "), None);
    }

    // Given an unrecognized format
    // When parsing it
    // Then no date is returned instead of panicking
    #[test]
    fn test_given_unrecognized_format_when_parsing_then_none_is_returned() {
        assert_eq!(parse_flexible_date("not-a-date"), None);
    }
}
