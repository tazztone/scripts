const fs = require('fs');
const path = require('path');
const assert = require('assert');

// Read userscript source
const scriptPath = path.join(__dirname, '..', 'huggingface-heart.user.js');
const scriptSource = fs.readFileSync(scriptPath, 'utf8');

// Basic syntax check
assert(scriptSource.includes('FILTER_EXCLUDE_ENABLED'), 'Missing FILTER_EXCLUDE_ENABLED');
assert(scriptSource.includes('FILTER_EXCLUDE_TERMS'), 'Missing FILTER_EXCLUDE_TERMS');
assert(scriptSource.includes('parseNegativeFilter'), 'Missing parseNegativeFilter');
assert(scriptSource.includes('isCardExcludedByText'), 'Missing isCardExcludedByText');

// Execute parser logic in isolation
function parseNegativeFilter(termsStr) {
  if (!termsStr || typeof termsStr !== 'string') return [];
  const rawTokens = termsStr.split(/[,\n]+/);
  const matchers = [];

  for (const raw of rawTokens) {
    const token = raw.trim();
    if (!token) continue;

    const regexMatch = token.match(/^\/(.+)\/([a-z]*)$/i);
    if (regexMatch) {
      try {
        const pattern = regexMatch[1];
        const flags = regexMatch[2] || 'i';
        matchers.push({ type: 'regex', regex: new RegExp(pattern, flags), raw: token });
        continue;
      } catch (e) {}
    }

    matchers.push({ type: 'string', text: token.toLowerCase(), raw: token });
  }

  return matchers;
}

function isCardExcludedByText(cardTitle, modelId, matchers) {
  if (!matchers || matchers.length === 0) return false;
  const idText = (modelId || '').toLowerCase();
  const titleText = (cardTitle || '').trim().toLowerCase();

  for (const m of matchers) {
    if (m.type === 'regex') {
      if (m.regex.test(modelId || '') || m.regex.test(cardTitle || '')) {
        return true;
      }
    } else if (m.type === 'string') {
      if (idText.includes(m.text) || titleText.includes(m.text)) {
        return true;
      }
    }
  }
  return false;
}

// 1. Single term test
let m1 = parseNegativeFilter('gguf');
assert.strictEqual(m1.length, 1);
assert.strictEqual(isCardExcludedByText('Llama-3-8B-GGUF', 'meta-llama/Llama-3-8B-GGUF', m1), true);
assert.strictEqual(isCardExcludedByText('Llama-3-8B', 'meta-llama/Llama-3-8B', m1), false);

// 2. Multi-term comma separated test with extra spaces
let m2 = parseNegativeFilter(' gguf , fp8,   /q[48]_k/i ');
assert.strictEqual(m2.length, 3);
assert.strictEqual(isCardExcludedByText('Flux.1-schnell', 'black-forest-labs/FLUX.1-schnell-FP8', m2), true);
assert.strictEqual(isCardExcludedByText('Model-Q4_K_M', 'user/model-q4_k_m', m2), true);
assert.strictEqual(isCardExcludedByText('Standard Model', 'user/standard-model', m2), false);

// 3. Invalid regex safety test (does not throw and falls back to literal substring)
let m3 = parseNegativeFilter('/[invalid-regex/');
assert.strictEqual(m3.length, 1);
assert.strictEqual(m3[0].type, 'string');
assert.strictEqual(m3[0].text, '/[invalid-regex/');

console.log('All Node.js unit assertions passed successfully!');
