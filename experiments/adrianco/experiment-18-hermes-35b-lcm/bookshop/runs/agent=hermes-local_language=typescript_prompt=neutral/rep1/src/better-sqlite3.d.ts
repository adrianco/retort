declare module 'better-sqlite3' {
  class Database {
    constructor(path: string);
    pragma(statement: string): any;
    exec(statement: string): this;
    close(): void;
    prepare(statement: string): Statement;
  }

  interface Statement {
    run(...params: any[]): { lastInsertRowid: number; changes: number };
    get(...params: any[]): any;
    all(...params: any[]): any[];
    raw(): this;
    bind(params: any): this;
  }

  const DatabaseModule: typeof Database;
  export = DatabaseModule;
}
