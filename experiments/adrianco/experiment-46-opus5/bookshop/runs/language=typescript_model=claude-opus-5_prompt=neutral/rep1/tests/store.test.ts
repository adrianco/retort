import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { BookStore, DuplicateIsbnError } from '../src/db.js';

let dir: string;

beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), 'books-store-'));
});

afterEach(() => {
  rmSync(dir, { recursive: true, force: true });
});

describe('BookStore', () => {
  it('persists books to disk across connections', () => {
    const file = join(dir, 'books.db');

    const first = new BookStore(file);
    const created = first.create({
      title: 'Dune',
      author: 'Frank Herbert',
      year: 1965,
      isbn: '9780441013593',
    });
    first.close();

    // Reopening the same file must see the previously written row.
    const second = new BookStore(file);
    expect(second.get(created.id)).toEqual(created);
    expect(second.list()).toEqual([created]);
    second.close();
  });

  it('raises DuplicateIsbnError but allows many books with no isbn', () => {
    const store = new BookStore(':memory:');
    const base = { author: 'Anon', year: null, isbn: null };

    // SQLite treats NULLs as distinct, so a UNIQUE isbn column still permits
    // any number of books without one.
    store.create({ ...base, title: 'One' });
    store.create({ ...base, title: 'Two' });
    expect(store.list()).toHaveLength(2);

    store.create({ ...base, title: 'Three', isbn: '9780441013593' });
    expect(() =>
      store.create({ ...base, title: 'Four', isbn: '9780441013593' }),
    ).toThrow(DuplicateIsbnError);

    store.close();
  });

  it('reports misses from update and delete without throwing', () => {
    const store = new BookStore(':memory:');
    expect(
      store.update(42, { title: 'X', author: 'Y', year: null, isbn: null }),
    ).toBeNull();
    expect(store.delete(42)).toBe(false);
    store.close();
  });
});
