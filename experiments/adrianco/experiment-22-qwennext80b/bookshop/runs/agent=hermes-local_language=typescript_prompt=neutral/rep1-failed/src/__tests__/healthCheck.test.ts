import request from 'supertest';
import app from '../server';

const api = request(app);

describe('Health Check', () => {
  it('should return 200 for health endpoint', async () => {
    const res = await api.get('/health');
    expect(res.status).toBe(200);
    expect(res.body.status).toBe('ok');
    expect(res.body.timestamp).toBeDefined();
    expect(typeof res.body.timestamp).toBe('string');
  });
});
