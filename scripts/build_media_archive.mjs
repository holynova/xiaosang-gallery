import {createHash} from 'node:crypto';
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import {dirname, join} from 'node:path';

const manifest = await readFile('catalog/archive.sha256', 'utf8');
const receipt = JSON.parse(await readFile('catalog/legacy-media.json', 'utf8'));
const entries = manifest.trimEnd().split('\n').map(line => {
  const match = /^([a-f0-9]{64})  ((?:media|originals)\/[\w./-]+)$/.exec(line);
  if (!match || match[2].split('/').some(part => !part || part === '..')) {
    throw new Error('Invalid media manifest entry');
  }
  return {hash: match[1], path: match[2]};
});
const digest = data => createHash('sha256').update(data).digest('hex');
const keys = entries.map(item => item.path).sort();
if (digest(keys.join('\n')) !== receipt.keysSha256 || keys.length !== receipt.objects) {
  throw new Error('Media manifest differs from the gallery catalog');
}

const out = 'archive-dist';
const oldSite = 'https://xiaosang.cc/xiaosang-gallery/';
const archive = 'https://gallery-media.xiaosang.cc/';
const pending = entries.values();
let complete = 0;
async function copyMedia() {
  for (const {hash, path} of pending) {
    let lastError;
    for (let attempt = 0; attempt < 5; attempt++) {
      try {
        const source = attempt % 2 ? archive : oldSite;
        const response = await fetch(new URL(path, source), {signal: AbortSignal.timeout(30000)});
        if (!response.ok) {
          await response.body?.cancel();
          throw new Error('HTTP ' + response.status);
        }
        const bytes = Buffer.from(await response.arrayBuffer());
        if (digest(bytes) !== hash) throw new Error('SHA-256 mismatch');
        const dest = join(out, path);
        await mkdir(dirname(dest), {recursive:true});
        await writeFile(dest, bytes);
        lastError = undefined;
        break;
      } catch (error) {
        lastError = error;
        await new Promise(resolve => setTimeout(resolve, (attempt + 1) * 700));
      }
    }
    if (lastError) throw new Error(path + ': ' + lastError.message);
    if (++complete % 500 === 0) console.log(complete + '/' + entries.length + ' verified');
  }
}
await Promise.all(Array.from({length:24}, copyMedia));
await mkdir(join(out,'migration'), {recursive:true});
await writeFile(join(out,'migration/legacy-v1.json'), JSON.stringify(receipt));
await writeFile(join(out,'_headers'), '/media/*\n  Cache-Control: public, max-age=604800\n/originals/*\n  Content-Disposition: attachment\n  Cache-Control: public, max-age=604800\n');
console.log('Verified ' + complete + ' objects');
