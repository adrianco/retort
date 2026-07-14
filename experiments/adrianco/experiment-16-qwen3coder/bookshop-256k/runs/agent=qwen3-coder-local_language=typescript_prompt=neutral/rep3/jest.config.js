module.exports = {
  transform: {
    '^.+\\.ts$': 'ts-jest'
  },
  testRegex: 'src/.*\\.test\\.ts$',
  moduleFileExtensions: ['ts', 'js'],
  collectCoverageFrom: [
    'src/**/*.{ts,js}',
    '!src/**/*.d.ts'
  ],
  coverageDirectory: 'coverage',
  testEnvironment: 'node'
};