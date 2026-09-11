import { createHash } from 'node:crypto';
export const contentHash = (bytes: Buffer) => createHash('sha256').update(bytes).digest('hex');
