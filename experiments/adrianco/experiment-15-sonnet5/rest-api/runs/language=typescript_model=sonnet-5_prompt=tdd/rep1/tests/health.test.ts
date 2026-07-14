import request from 'supertest';
import { createApp } from '../src/app';
import { createDb } from '../src/db';

describe('GET /health', () => {
  it('returns 200 with status ok', async () => {
    const db = createDb(':memory:');
    const app = createApp(db);

    const res = await request(app).get('/health');

    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: 'ok' });
  });
});
