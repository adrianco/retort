#!/usr/bin/env ts-node
import { runInThisContext } from 'vm';
import * as fs from 'fs';

// Read the index.ts file and execute it
const indexCode = fs.readFileSync(__dirname + '/index.ts', 'utf-8');
runInThisContext(indexCode);
