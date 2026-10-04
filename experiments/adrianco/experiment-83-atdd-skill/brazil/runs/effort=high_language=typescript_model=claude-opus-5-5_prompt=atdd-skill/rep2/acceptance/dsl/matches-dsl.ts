/**
 * DSL: finding matches.
 */
import type { WorldRef } from './soccer-dsl.js';
import type { MatchCriteria } from '../drivers/soccer-system-driver.js';

export class MatchesDsl {
  constructor(private readonly world: WorldRef) {}

  async confirmMeetings({ team, opponent, expected }: { team: string; opponent: string; expected: string[] }) {
    await (await this.world().system()).confirmMatchesFound({ team, opponent }, expected);
  }

  async confirmFound({ expected, ...criteria }: MatchCriteria & { expected: string[] }) {
    await (await this.world().system()).confirmMatchesFound(criteria, expected);
  }

  async confirmFoundAtLeast({ count, involving = [], ...criteria }: MatchCriteria & { count: number; involving?: string[] }) {
    await (await this.world().system()).confirmMatchesFoundAtLeast(criteria, count, involving);
  }

  async confirmLastMeeting({ team, opponent, expected }: { team: string; opponent: string; expected: string }) {
    await (await this.world().system()).confirmLastMeeting(team, opponent, expected);
  }

  async confirmLastMeetingFound({ team, opponent }: { team: string; opponent: string }) {
    await (await this.world().system()).confirmLastMeeting(team, opponent);
  }

  async confirmDerbies({ season, expected }: { season?: number; expected: string[] }) {
    await (await this.world().system()).confirmDerbies({ season }, expected);
  }

  async confirmDerbiesFound({ season, including }: { season?: number; including: string[] }) {
    await (await this.world().system()).confirmDerbiesInclude({ season }, including);
  }

  async confirmReadableAnswer({ mentions, ...criteria }: MatchCriteria & { mentions: string[] }) {
    await (await this.world().system()).confirmMatchAnswerMentions(criteria, mentions);
  }
}
