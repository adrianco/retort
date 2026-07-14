import { app, initDatabase } from '../src/server';
import request from 'supertest';

describe('Book Collection API - Simple Test', () => {
  beforeAll(async () => {
    await initDatabase();
  });

  it('should respond to health check', async () => {
    const response = await request(app).get('/health');
    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('status', 'OK');
  });
});