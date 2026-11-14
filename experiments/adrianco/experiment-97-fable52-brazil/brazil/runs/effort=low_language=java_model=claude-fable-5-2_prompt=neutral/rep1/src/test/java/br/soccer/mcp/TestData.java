package br.soccer.mcp;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Path;

/** Loads the real Kaggle CSV files once for all test classes. */
final class TestData {
    static final DataStore STORE;
    static final SoccerService SERVICE;
    static final Tools TOOLS;

    static {
        try {
            STORE = DataStore.load(Path.of("data", "kaggle"));
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        SERVICE = new SoccerService(STORE);
        TOOLS = new Tools(SERVICE);
    }

    private TestData() {}
}
