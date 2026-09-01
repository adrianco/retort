const express = require('express');
const bookRoutes = require('./routes');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

app.get('/health', (_req, res) => {
  return res.status(200).json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.use('/api', bookRoutes);

app.use((_req, res) => {
  return res.status(404).json({ error: 'Not found' });
});

app.use((err, _req, res, _next) => {
  console.error('Unhandled error:', err.message);
  return res.status(500).json({ error: 'Internal server error' });
});

module.exports = { app, PORT };
