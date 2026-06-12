import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { DataLoader } from './loader.js';
import { createServer } from './server.js';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '..', 'data', 'kaggle');

async function main() {
  const loader = new DataLoader(DATA_DIR);

  process.stderr.write('Loading Brazilian soccer data...\n');
  await loader.load();
  process.stderr.write('Data loaded. Starting MCP server...\n');

  const server = createServer(loader);
  const transport = new StdioServerTransport();
  await server.connect(transport);
  process.stderr.write('Brazilian Soccer MCP server running on stdio\n');
}

main().catch((err) => {
  process.stderr.write(`Fatal error: ${err}\n`);
  process.exit(1);
});
