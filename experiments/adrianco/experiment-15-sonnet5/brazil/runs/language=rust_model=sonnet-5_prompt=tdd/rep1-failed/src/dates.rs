use chrono::NaiveDate;

/// Parses a date string in any of the formats found in the provided datasets:
/// ISO date ("2023-09-24"), ISO datetime ("2012-05-19 18:30:00"), or
/// Brazilian day/month/year ("29/03/2003"). Returns `None` if none match.
pub fn parse_flexible_date(input: &str) -> Option<NaiveDate> {
    let input = input.trim();
    if let Ok(dt) = NaiveDate::parse_from_str(input, "%Y-%m-%d") {
        return Some(dt);
    }
    if let Ok(dt) = chrono::NaiveDateTime::parse_from_str(input, "%Y-%m-%d %H:%M:%S") {
        return Some(dt.date());
    }
    if let Ok(dt) = NaiveDate::parse_from_str(input, "%d/%m/%Y") {
        return Some(dt);
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_iso_date() {
        assert_eq!(
            parse_flexible_date("2023-09-24").unwrap(),
            chrono::NaiveDate::from_ymd_opt(2023, 9, 24).unwrap()
        );
    }

    #[test]
    fn parses_iso_datetime_with_time_component() {
        assert_eq!(
            parse_flexible_date("2012-05-19 18:30:00").unwrap(),
            chrono::NaiveDate::from_ymd_opt(2012, 5, 19).unwrap()
        );
    }

    #[test]
    fn parses_brazilian_date_format() {
        assert_eq!(
            parse_flexible_date("29/03/2003").unwrap(),
            chrono::NaiveDate::from_ymd_opt(2003, 3, 29).unwrap()
        );
    }

    #[test]
    fn rejects_unparseable_date() {
        assert!(parse_flexible_date("not-a-date").is_none());
    }
}
