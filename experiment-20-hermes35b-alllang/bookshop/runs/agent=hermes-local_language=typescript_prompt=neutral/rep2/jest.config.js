module.exports = {
  testEnvironment: 'node',
  testMatch: ['<rootDir>/dist/tests.spec.js'],
  moduleFileExtensions: ['js', 'ts', 'json'],
  forceExit: true,
  detectOpenHandles: true,
  testTimeout: 10000
};
