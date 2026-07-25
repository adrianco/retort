package com.brazilsoccer.mcp.util;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.time.LocalTime;

import static org.assertj.core.api.Assertions.assertThat;

/** The datasets mix ISO, ISO+time and Brazilian date formats, plus NA placeholders. */
class DateParsersTest {

    @Test
    @DisplayName("all three date formats found in the datasets are supported")
    void parsesEveryDateFormat() {
        assertThat(DateParsers.parseDate("2023-09-24")).contains(LocalDate.of(2023, 9, 24));
        assertThat(DateParsers.parseDate("2012-05-19 18:30:00")).contains(LocalDate.of(2012, 5, 19));
        assertThat(DateParsers.parseDate("29/03/2003")).contains(LocalDate.of(2003, 3, 29));
    }

    @Test
    @DisplayName("placeholders and malformed values yield no date")
    void rejectsPlaceholders() {
        assertThat(DateParsers.parseDate("NA")).isEmpty();
        assertThat(DateParsers.parseDate("-")).isEmpty();
        assertThat(DateParsers.parseDate(null)).isEmpty();
        assertThat(DateParsers.parseDate("not a date")).isEmpty();
    }

    @Test
    void parsesKickOffTimes() {
        assertThat(DateParsers.parseTime("2012-05-19 18:30:00")).contains(LocalTime.of(18, 30));
        assertThat(DateParsers.parseTime("20:00:00")).contains(LocalTime.of(20, 0));
        assertThat(DateParsers.parseTime("2023-09-24")).isEmpty();
    }

    @Test
    @DisplayName("goals may be written as integers, as decimals or as NA")
    void parsesGoals() {
        assertThat(DateParsers.parseInt("3")).contains(3);
        assertThat(DateParsers.parseInt("3.0")).contains(3);
        assertThat(DateParsers.parseInt("NA")).isEmpty();
        assertThat(DateParsers.parseInt("-")).isEmpty();
        assertThat(DateParsers.parseInt("")).isEmpty();
    }
}
