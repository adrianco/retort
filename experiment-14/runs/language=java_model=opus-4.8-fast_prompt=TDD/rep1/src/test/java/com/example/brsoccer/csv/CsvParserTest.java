package com.example.brsoccer.csv;

import org.junit.jupiter.api.Test;

import java.io.StringReader;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class CsvParserTest {

    @Test
    void parsesSimpleCommaSeparatedRow() {
        List<List<String>> rows = CsvParser.parse(new StringReader("a,b,c\n1,2,3\n"));
        assertEquals(2, rows.size());
        assertEquals(List.of("a", "b", "c"), rows.get(0));
        assertEquals(List.of("1", "2", "3"), rows.get(1));
    }

    @Test
    void handlesQuotedFieldsContainingCommas() {
        List<List<String>> rows = CsvParser.parse(new StringReader("\"Santos, SP\",2\n"));
        assertEquals(1, rows.size());
        assertEquals(List.of("Santos, SP", "2"), rows.get(0));
    }

    @Test
    void handlesEscapedDoubleQuotesInsideQuotedField() {
        List<List<String>> rows = CsvParser.parse(new StringReader("\"say \"\"hi\"\"\",x\n"));
        assertEquals(List.of("say \"hi\"", "x"), rows.get(0));
    }

    @Test
    void stripsUtf8ByteOrderMarkFromFirstField() {
        List<List<String>> rows = CsvParser.parse(new StringReader("﻿id,name\n"));
        assertEquals(List.of("id", "name"), rows.get(0));
    }

    @Test
    void preservesUnicodeAccentedCharacters() {
        List<List<String>> rows = CsvParser.parse(new StringReader("São Paulo,Grêmio\n"));
        assertEquals(List.of("São Paulo", "Grêmio"), rows.get(0));
    }

    @Test
    void ignoresBlankLines() {
        List<List<String>> rows = CsvParser.parse(new StringReader("a,b\n\n1,2\n"));
        assertEquals(2, rows.size());
    }

    @Test
    void keepsEmptyTrailingFields() {
        List<List<String>> rows = CsvParser.parse(new StringReader("a,b,\n"));
        assertEquals(List.of("a", "b", ""), rows.get(0));
    }
}
