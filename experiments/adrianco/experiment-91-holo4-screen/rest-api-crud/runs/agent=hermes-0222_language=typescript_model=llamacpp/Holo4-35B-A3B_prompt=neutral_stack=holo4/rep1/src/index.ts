import express, { Request, Response } from 'express';
import bookRoutes from './routes';
import { handleError, parseBody } from './middleware';

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(parseBody);

// Health check
app.get('/health', (req: Request, res: Response) => {
  res.status(200).json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Routes
app.use('/', bookRoutes);

// Error handling
app.use(handleError);

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

export default app;
