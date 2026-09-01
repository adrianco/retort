const { app, PORT } = require('./app');
const { closeDb } = require('./db');

const server = app.listen(PORT, () => {
  console.log(`Book API server running on port ${PORT}`);
});

process.on('SIGINT', () => {
  console.log('Shutting down...');
  closeDb();
  server.close(() => {
    process.exit(0);
  });
});

process.on('SIGTERM', () => {
  console.log('Shutting down...');
  closeDb();
  server.close(() => {
    process.exit(0);
  });
});
