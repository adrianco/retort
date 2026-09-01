import express from 'express';
import bookRoutes from './routes';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());
app.use(bookRoutes);

if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
  });
}

export default app;
