package com.brazilsoccer.mcp.util;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/** The CSV reader has to survive every convention used by the bundled Kaggle files. */
class CsvReaderTest {

    @TempDir
    Path folder;

    private Path write(String name, String content) throws IOException {
        Path file = folder.resolve(name);
        Files.writeString(file, content, StandardCharsets.UTF_8);
        return file;
    }

    @Test
    @DisplayName("quoted fields may contain commas, like the FIFA 'Joined' column")
    void parsesQuotedFieldsWithCommas() throws IOException {
        Path file = write("players.csv", "Name,Joined,Club\nL. Messi,\"Jul 1, 2004\",FC Barcelona\n");

        List<CsvReader.Row> rows = CsvReader.readAll(file);

        assertThat(rows).hasSize(1);
        assertThat(rows.get(0).get("Joined")).isEqualTo("Jul 1, 2004");
        assertThat(rows.get(0).get("Club")).isEqualTo("FC Barcelona");
    }

    @Test
    @DisplayName("a UTF-8 BOM and accented Portuguese text are read correctly")
    void handlesBomAndAccents() throws IOException {
        Path file = write("teams.csv", "﻿home_team,away_team\nSão Paulo,Grêmio\nAvaí,Atlético-MG\n");

        List<CsvReader.Row> rows = CsvReader.readAll(file);

        assertThat(rows).hasSize(2);
        assertThat(rows.get(0).get("home_team")).isEqualTo("São Paulo");
        assertThat(rows.get(0).get("away_team")).isEqualTo("Grêmio");
        assertThat(rows.get(1).get("home_team")).isEqualTo("Avaí");
    }

    @Test
    @DisplayName("escaped quotes, CRLF line endings and empty cells")
    void handlesEscapedQuotesAndCrlf() throws IOException {
        Path file = write("odd.csv", "a,b,c\r\n\"say \"\"hi\"\"\",,3\r\n");

        List<CsvReader.Row> rows = CsvReader.readAll(file);

        assertThat(rows).hasSize(1);
        assertThat(rows.get(0).get("a")).isEqualTo("say \"hi\"");
        assertThat(rows.get(0).get("b")).isNull();
        assertThat(rows.get(0).get("c")).isEqualTo("3");
    }

    @Test
    @DisplayName("a quoted field may span several physical lines")
    void handlesEmbeddedNewlines() throws IOException {
        Path file = write("multiline.csv", "id,note\n1,\"line one\nline two\"\n2,plain\n");

        List<CsvReader.Row> rows = CsvReader.readAll(file);

        assertThat(rows).hasSize(2);
        assertThat(rows.get(0).get("note")).isEqualTo("line one\nline two");
        assertThat(rows.get(1).get("note")).isEqualTo("plain");
    }

    @Test
    @DisplayName("missing columns and trailing blank lines are ignored")
    void toleratesMissingColumns() throws IOException {
        Path file = write("short.csv", "a,b\n1,2\n\n");

        List<CsvReader.Row> rows = CsvReader.readAll(file);

        assertThat(rows).hasSize(1);
        assertThat(rows.get(0).get("does-not-exist")).isNull();
        assertThat(rows.get(0).getOrDefault("does-not-exist", "fallback")).isEqualTo("fallback");
    }
}
