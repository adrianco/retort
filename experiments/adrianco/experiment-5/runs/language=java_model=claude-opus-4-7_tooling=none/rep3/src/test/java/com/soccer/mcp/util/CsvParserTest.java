package com.soccer.mcp.util;

import org.junit.jupiter.api.Test;

import java.io.StringReader;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;

class CsvParserTest {

    @Test
    void givenSimpleCsv_whenParsed_thenSplitsByComma() throws Exception {
        String csv = "a,b,c\n1,2,3\n";
        List<List<String>> rows = CsvParser.parseAll(new StringReader(csv));
        assertEquals(2, rows.size());
        assertEquals(List.of("a", "b", "c"), rows.get(0));
        assertEquals(List.of("1", "2", "3"), rows.get(1));
    }

    @Test
    void givenQuotedFieldWithComma_whenParsed_thenKeepsCommaInsideField() throws Exception {
        String csv = "name,note\n\"Smith, John\",hello\n";
        List<List<String>> rows = CsvParser.parseAll(new StringReader(csv));
        assertEquals(2, rows.size());
        assertEquals(List.of("Smith, John", "hello"), rows.get(1));
    }

    @Test
    void givenEscapedQuoteInsideQuotedField_whenParsed_thenUnescapes() throws Exception {
        String csv = "a,b\n\"he said \"\"hi\"\"\",bye\n";
        List<List<String>> rows = CsvParser.parseAll(new StringReader(csv));
        assertEquals(2, rows.size());
        assertEquals(List.of("he said \"hi\"", "bye"), rows.get(1));
    }

    @Test
    void givenCrlfLineEndings_whenParsed_thenSplitsRows() throws Exception {
        String csv = "a,b\r\n1,2\r\n";
        List<List<String>> rows = CsvParser.parseAll(new StringReader(csv));
        assertEquals(2, rows.size());
        assertEquals(List.of("1", "2"), rows.get(1));
    }

    @Test
    void givenEmptyTrailingField_whenParsed_thenPreservesEmptyString() throws Exception {
        String csv = "a,b,c\n1,2,\n";
        List<List<String>> rows = CsvParser.parseAll(new StringReader(csv));
        assertEquals(List.of("1", "2", ""), rows.get(1));
    }
}
