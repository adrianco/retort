import { createServer } from 'node:http';
import { openCollection } from './books.js';

const collection = openCollection(process.env.DB_PATH ?? 'books.sqlite');
const server = createServer(async (incoming, outgoing) => {
  try {
    const method = incoming.method ?? 'GET';
    const chunks: Buffer[] = [];
    let size = 0;
    for await (const chunk of incoming) {
      size += chunk.length;
      if (size > 1024 * 1024) {
        outgoing.writeHead(413, { 'Content-Type': 'application/json' });
        outgoing.end(JSON.stringify({ error: 'Body exceeds 1 MiB' }));
        return;
      }
      chunks.push(chunk);
    }
    const request = new Request('http://localhost' + incoming.url, {
      method,
      body: method === 'GET' || method === 'HEAD' ? undefined : Buffer.concat(chunks)
    });
    const response = await collection.handle(request);
    outgoing.writeHead(response.status, Object.fromEntries(response.headers));
    outgoing.end(await response.text());
  } catch (err) {
    console.error(err);
    outgoing.writeHead(500, { 'Content-Type': 'application/json' });
    outgoing.end(JSON.stringify({ error: 'Internal server error' }));
  }
});
server.listen(Number(process.env.PORT ?? 3000));
server.on('close', collection.close);
for (const signal of ['SIGTERM', 'SIGINT']) process.once(signal, () => server.close());
