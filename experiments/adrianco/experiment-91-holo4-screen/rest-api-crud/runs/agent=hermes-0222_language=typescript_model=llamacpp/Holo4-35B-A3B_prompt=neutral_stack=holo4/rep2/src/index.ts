import { app, PORT } from './app';

app.listen(PORT, () => {
  console.log(`Book API server running on port ${PORT}`);
});
