import express from "express";
import bookRoutes from "./routes";

const app = express();

// Middleware
app.use(express.json());

// Routes
app.use("/books", bookRoutes);

// Health check
app.get("/health", (_req: express.Request, res: express.Response) => {
  res.status(200).json({ status: "ok" });
});

// 404 handler
app.use((_req: express.Request, res: express.Response) => {
  res.status(404).json({ error: "Not found" });
});

// Error handler
app.use(
  (
    err: Error,
    _req: express.Request,
    res: express.Response,
    _next: express.NextFunction
  ) => {
    console.error(err.stack);
    res.status(500).json({ error: "Internal server error" });
  }
);

export { app };
