import { app } from "./app";
import { closeDatabase } from "./db";

const PORT = process.env.PORT || 3000;

const server = app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

// Graceful shutdown
process.on("SIGINT", () => {
  console.log("Shutting down...");
  closeDatabase();
  server.close(() => {
    process.exit(0);
  });
});

process.on("SIGTERM", () => {
  console.log("Shutting down...");
  closeDatabase();
  server.close(() => {
    process.exit(0);
  });
});

export { server };
