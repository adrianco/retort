/**
 * DSL: what the system knows about the provided datasets, and how promptly
 * it answers questions about them.
 */
import type { SoccerDriver } from '../drivers/soccer-driver.js';

export class DatasetsDsl {
  constructor(private readonly driver: SoccerDriver) {}

  async requestOverview(): Promise<void> {
    await this.driver.requestDatasetOverview();
  }

  confirmLoaded({ dataset, records }: { dataset: string; records: number }): void {
    this.driver.confirmDatasetLoaded(dataset, records);
  }
}

export class AnswersDsl {
  private elapsedMs: number | undefined;

  constructor(private readonly driver: SoccerDriver) {}

  async timeAnswerTo(question: () => Promise<void>): Promise<void> {
    const started = performance.now();
    await question();
    this.elapsedMs = performance.now() - started;
  }

  confirmAnsweredWithin({ seconds }: { seconds: number }): void {
    if (this.elapsedMs === undefined) throw new Error('No question has been asked yet');
    this.driver.confirmLastQuestionAnswered();
    if (this.elapsedMs > seconds * 1000) {
      throw new Error(`Expected an answer within ${seconds}s but it took ${(this.elapsedMs / 1000).toFixed(2)}s`);
    }
  }
}
