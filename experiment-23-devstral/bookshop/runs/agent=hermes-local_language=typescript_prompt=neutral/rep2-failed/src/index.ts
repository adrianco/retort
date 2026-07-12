import express from 'express';
import bodyParser from 'body-parser';
import bookRoutes from './routes/bookRoutes';
import { Database } from './db/database';

const app = express();
const db = new Database();

app.use(bodyParser.json());
app.use('/', bookRoutes);

async function startServer() {
    try {
        await db.init();
        
        const PORT = process.env.PORT || 3000;
        app.listen(PORT, () => {
            console.log(`Server is running on port ${PORT}`);
        });
    } catch (err) {
        console.error('Failed to start server:', err);
        process.exit(1);
    }
}

startServer();
