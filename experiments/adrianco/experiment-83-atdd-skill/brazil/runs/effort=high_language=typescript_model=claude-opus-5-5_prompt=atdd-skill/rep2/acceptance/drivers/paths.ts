/** Locations the drivers need: the built server and the provided data. */
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
// Works both from source (acceptance/drivers) and compiled (dist/acceptance/drivers).
const root = here.includes(`${path.sep}dist${path.sep}`) ? path.resolve(here, '../../..') : path.resolve(here, '../..');

export const PROJECT_ROOT = root;
export const SERVER_ENTRY = path.join(root, 'dist', 'src', 'server.js');
export const PROVIDED_DATA_DIR = path.join(root, 'data', 'kaggle');
