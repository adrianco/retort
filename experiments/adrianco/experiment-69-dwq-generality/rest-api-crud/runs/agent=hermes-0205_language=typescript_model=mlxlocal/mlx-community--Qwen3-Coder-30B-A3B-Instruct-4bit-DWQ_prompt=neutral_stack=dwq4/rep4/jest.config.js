{
  "testEnvironment": "node",
  "collectCoverageFrom": [
    "src/**/*.{js}",
    "!src/index.js"
  ],
  "coverageDirectory": "coverage",
  "coverageReporters": ["text", "lcov"],
  "testMatch": [
    "**/__tests__/**/*.js",
    "**/?(*.)+(spec|test).js"
  ]
}