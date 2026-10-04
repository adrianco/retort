package br.soccer;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Path;

/** Loads the real Kaggle datasets once for all test classes ("Given the data is loaded"). */
final class TestData {
    static final DataStore STORE;
    static final QueryService QUERIES;

    static {
        try {
            STORE = DataStore.load(Path.of("data/kaggle"));
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        QUERIES = new QueryService(STORE);
    }

    private TestData() {}
}
