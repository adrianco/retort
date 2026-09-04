const request = require('supertest');
const { app, initDB } = require('./src/index.js');

describe('Book API', () => {
  beforeAll(async () => {
    await initDB();
  });

  test('Health check endpoint', async () => {
    const response = await request(app).get('/health');
    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('status', 'OK');
  });
});