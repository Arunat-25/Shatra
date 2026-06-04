#!/usr/bin/env node
/** Generates docs/alt-translation-template.md from locale JSON files. */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const localesDir = path.join(root, 'frontend/src/locales');

const ru = JSON.parse(fs.readFileSync(path.join(localesDir, 'ru.json'), 'utf8'));
const en = JSON.parse(fs.readFileSync(path.join(localesDir, 'en.json'), 'utf8'));
const alt = JSON.parse(fs.readFileSync(path.join(localesDir, 'alt.json'), 'utf8'));

const DISTRICTS = [
  'Кош-Агач',
  'Майма',
  'Онгудай',
  'Турочак',
  'Улаган',
  'Усть-Кан',
  'Усть-Кокса',
  'Чемал',
  'Чоя',
  'Шебалино',
  'Горно-Алтайск',
  'Другое',
];

function flat(obj, prefix = '') {
  const out = [];
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      out.push(...flat(v, key));
    } else {
      out.push([key, v]);
    }
  }
  return out;
}

function get(obj, dotPath) {
  return dotPath.split('.').reduce((o, p) => o?.[p], obj);
}

function esc(s) {
  return String(s).replace(/\|/g, '\\|').replace(/\n/g, ' ');
}

const rows = flat(ru);
let md = `# Шаблон перевода ALT (алтайский)

Кнопка **ALT** в шапке сайта переключает интерфейс на \`frontend/src/locales/alt.json\`.

Заполните колонку **Ваш перевод** и пришлите этот файл (или таблицу) — обновлю \`alt.json\`.

**Не меняйте плейсхолдеры:** \`{{count}}\`, \`{{color}}\`, \`{{n}}\`, \`{{status}}\` — подставляются кодом.

Всего строк UI: **${rows.length}**

| Ключ | RU | EN | ALT (сейчас) | Ваш перевод |
|------|----|----|--------------|-------------|
`;

for (const [key, ruVal] of rows) {
  const enVal = get(en, key) ?? '';
  const altVal = get(alt, key) ?? '';
  md += `| \`${key}\` | ${esc(ruVal)} | ${esc(enVal)} | ${esc(altVal)} | |\n`;
}

md += `
## Районы (выпадающий список в профиле)

Сейчас только на русском (\`frontend/src/constants/profile.js\`). Если нужен ALT — переведите и пришлите.

| RU | Ваш перевод |
|----|-------------|
`;
for (const d of DISTRICTS) {
  md += `| ${esc(d)} | |\n`;
}

const outPath = path.join(root, 'docs/alt-translation-template.md');
fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, md, 'utf8');
console.log(`Wrote ${outPath} (${rows.length} UI strings + ${DISTRICTS.length} districts)`);
