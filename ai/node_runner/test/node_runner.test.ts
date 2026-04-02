import test from 'node:test';
import assert from 'node:assert/strict';

import { makeJsonOutputWriter, parseRunnerInput } from '../src/index.js';

test('parseRunnerInput rejects invalid payloads', () => {
  assert.throws(
    () => parseRunnerInput('{"workspaceRoot": 123}'),
    /workspaceRoot/,
  );
});

test('parseRunnerInput accepts vanilla strategy payloads', () => {
  const parsed = parseRunnerInput(JSON.stringify({
    workspaceRoot: '/tmp/workspace',
    prompt: 'inspect the source and summarize findings',
    model: 'claude-sonnet-4-6',
    provider: 'anthropic',
    strategy: 'tasks',
    traceEnabled: true,
    loopDetection: {
      maxRepetitions: 3,
      loopDetectionWindow: 5,
      onLoopDetected: 'warn',
    },
    approvalMode: 'auto_approve',
    beforeRun: {
      promptPrefix: 'Use strict evidence.',
    },
    afterRun: {
      outputSuffix: 'End of reviewed output.',
    },
    tasks: [
      {
        title: 'Inspect source',
        description: 'Read the source tree and identify important files.',
        assignee: 'researcher',
      },
    ],
    agents: [
      {
        name: 'researcher',
        role: 'researcher',
      },
    ],
  }));

  assert.equal(parsed.strategy, 'tasks');
  assert.equal(parsed.traceEnabled, true);
  assert.equal(parsed.loopDetection?.maxRepetitions, 3);
  assert.equal(parsed.approvalMode, 'auto_approve');
  assert.equal(parsed.approvalControlPath, undefined);
  assert.equal(parsed.beforeRun?.promptPrefix, 'Use strict evidence.');
  assert.equal(parsed.afterRun?.outputSuffix, 'End of reviewed output.');
  assert.equal(parsed.tasks?.[0]?.title, 'Inspect source');
  assert.equal(parsed.agents?.[0]?.name, 'researcher');
});

test('parseRunnerInput accepts fanout payloads', () => {
  const parsed = parseRunnerInput(JSON.stringify({
    workspaceRoot: '/tmp/workspace',
    prompt: 'analyze this from multiple perspectives',
    model: 'gpt-4.1',
    provider: 'openai',
    strategy: 'fanout',
    fanout: {
      analysts: [
        { name: 'optimist', role: 'optimist' },
        { name: 'skeptic', role: 'skeptic' },
      ],
      synthesizer: { name: 'synthesizer', role: 'synthesizer' },
    },
  }));

  assert.equal(parsed.strategy, 'fanout');
  assert.equal(parsed.fanout?.analysts?.length, 2);
  assert.equal(parsed.fanout?.synthesizer?.name, 'synthesizer');
});

test('parseRunnerInput accepts new providers', () => {
  for (const provider of ['copilot', 'gemini', 'grok'] as const) {
    const parsed = parseRunnerInput(JSON.stringify({
      workspaceRoot: '/tmp/workspace',
      prompt: 'hello',
      model: 'demo-model',
      provider,
    }));
    assert.equal(parsed.provider, provider);
  }
});

test('makeJsonOutputWriter serializes newline-delimited events', () => {
  const chunks: string[] = [];
  const writeEvent = makeJsonOutputWriter({
    write(chunk) {
      chunks.push(typeof chunk === 'string' ? chunk : Buffer.from(chunk).toString('utf8'));
      return true;
    },
  });

  writeEvent({ type: 'run_started', data: { workspaceRoot: '/tmp/workspace', model: 'claude', provider: 'anthropic', strategy: 'agent' } });

  assert.deepEqual(chunks, [
    '{"type":"run_started","data":{"workspaceRoot":"/tmp/workspace","model":"claude","provider":"anthropic","strategy":"agent"}}\n',
  ]);
});
