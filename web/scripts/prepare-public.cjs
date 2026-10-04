// Runs the Python data pipeline before every build and verifies its output.
// Fails loudly (non-zero exit) when the pipeline errors or the expected
// JSON files are absent from web/public/ afterwards.
const { execSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const webDir = path.resolve(__dirname, '..');
const publicDir = path.join(webDir, 'public');
const required = ['market.json', 'trades.json', 'analytics.json'];

function fail(message) {
  console.error(`[prepare-public] ERROR: ${message}`);
  process.exit(1);
}

try {
  execSync('python3 ../services/main.py build', { cwd: webDir, stdio: 'inherit' });
} catch (err) {
  fail('data pipeline failed (python3 ../services/main.py build). See output above.');
}

const missing = required.filter((f) => !fs.existsSync(path.join(publicDir, f)));
if (missing.length > 0) {
  fail(`missing required data files in web/public/ after pipeline run: ${missing.join(', ')}`);
}

for (const f of required) {
  try {
    JSON.parse(fs.readFileSync(path.join(publicDir, f), 'utf8'));
  } catch (err) {
    fail(`${f} exists but is not valid JSON: ${err.message}`);
  }
}

console.log(`[prepare-public] OK: ${required.join(', ')} present in web/public/`);
