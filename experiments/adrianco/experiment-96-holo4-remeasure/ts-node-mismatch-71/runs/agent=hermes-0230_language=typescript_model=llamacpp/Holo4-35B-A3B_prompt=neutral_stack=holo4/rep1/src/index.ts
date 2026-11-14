import express from 'express';
import { clearAllBooks, initializeDatabase } from './database';
import bookRoutes from './routes';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

initializeDatabase();
app.use('/api', bookRoutes);

if (process.env.NODE_ENV !== 'test') {
  app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
  });
}

export default app;
