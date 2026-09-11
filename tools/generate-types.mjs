import { compile } from 'json-schema-to-typescript';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
const schema = JSON.parse(await readFile('contracts/0.1/schema.json', 'utf8'));
const result = await compile(schema, 'SceneScoreRecord', { bannerComment: '/* Generated from contracts/0.1/schema.json. Do not edit. */', unreachableDefinitions: true });
await mkdir('packages/contracts', { recursive: true });
await writeFile('packages/contracts/generated.d.ts', result);
