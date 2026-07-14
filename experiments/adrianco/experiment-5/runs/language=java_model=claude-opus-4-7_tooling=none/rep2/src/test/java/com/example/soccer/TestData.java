package com.example.soccer;

import com.example.soccer.data.DataStore;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/** Locates the bundled Kaggle dataset relative to the project root. */
public final class TestData {

    private TestData() {}

    public static Path kaggleDir() {
        Path cwd = Paths.get(".").toAbsolutePath().normalize();
        for (int i = 0; i < 5; i++) {
            Path candidate = cwd.resolve("data/kaggle");
            if (Files.isDirectory(candidate)) return candidate;
            cwd = cwd.getParent();
            if (cwd == null) break;
        }
        return Paths.get("data/kaggle");
    }

    public static DataStore load() throws IOException {
        DataStore store = new DataStore(kaggleDir());
        store.loadAll();
        return store;
    }
}
