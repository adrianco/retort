import { app, initDatabase } from '../src/server';
import request from 'supertest';

describe('Book Collection API - Unit Tests', () => {
  beforeAll(async () => {
    await initDatabase();
  });

  it('should initialize database successfully', async () => {
    // This test verifies the database initialization works
    const response = await request(app).get('/health');
    expect(response.status).toBe(200);
  });

  it('should return 400 for invalid book creation', async () => {
    const response = await request(app)
      .post('/books')
      .send({ title: '', author: 'Test Author' })
      .expect(400);
    
    expect(response.body).toHaveProperty('error', 'Title and author are required');
  });
});