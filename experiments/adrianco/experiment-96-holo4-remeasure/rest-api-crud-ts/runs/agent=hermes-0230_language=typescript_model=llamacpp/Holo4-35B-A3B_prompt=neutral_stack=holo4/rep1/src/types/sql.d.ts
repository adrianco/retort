declare module 'sql.js' {
  interface SqlJsDatabase {
    run(sql: string, params?: any[]): void;
    exec(sql: string): { columns: string[]; values: any[][] }[];
    export(): Uint8Array;
  }

  interface SqlJsConstructor {
    new (data?: Uint8Array | Buffer | null): SqlJsDatabase;
  }

  interface SqlJs {
    Database: SqlJsConstructor;
  }

  function initSqlJs(config?: { locateFile?: (url: string) => string }): Promise<SqlJs>;
  export = initSqlJs;
}
