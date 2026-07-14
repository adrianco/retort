package com.brsoccer.mcp;

import com.brsoccer.mcp.server.SoccerKnowledgeBase;

import java.io.IOException;
import java.nio.file.Path;
import java.nio.file.Paths;

/** Shared, lazily-loaded knowledge base for tests. */
public final class TestData {
    private static volatile SoccerKnowledgeBase kb;

    private TestData() {}

    public static SoccerKnowledgeBase get() {
        if (kb == null) {
            synchronized (TestData.class) {
                if (kb == null) {
                    try {
                        kb = new SoccerKnowledgeBase(dataDir());
                    } catch (IOException e) {
                        throw new RuntimeException(e);
                    }
                }
            }
        }
        return kb;
    }

    public static Path dataDir() {
        return Paths.get("data", "kaggle");
    }
}
