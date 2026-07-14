declare module 'sqlite' {
  export function open(options: { filename: string; driver: any }): Promise<any>;
}