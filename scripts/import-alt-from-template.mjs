#!/usr/bin/env node
/**
 * Import "Ваш перевод" column from docs/alt-translation-template.md into alt.json.
 * Replaces н' with ҥ in all string values.
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const templatePath = path.join(root, 'docs/alt-translation-template.md');
const ruPath = path.join(root, 'frontend/src/locales/ru.json');
const enPath = path.join(root, 'frontend/src/locales/en.json');
const altPath = path.join(root, 'frontend/src/locales/alt.json');

const ru = JSON.parse(fs.readFileSync(ruPath, 'utf8'));
const md = fs.readFileSync(templatePath, 'utf8');

/** @param {string} s */
function fixNg(s) {
  return s
    .trim()
    .replace(/н'/g, 'ҥ')
    .replace(/Н'/g, 'ҥ')
    .replace(/\{\{\s*(\w+)\s*\}\}/g, '{{$1}}');
}

/** @param {Map<string, string>} translations @param {object} source @param {string} [prefix] */
function buildLocale(translations, source, prefix = '') {
  const out = {};
  for (const [k, v] of Object.entries(source)) {
    const dotPath = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      out[k] = buildLocale(translations, v, dotPath);
    } else {
      const translated = translations.get(dotPath);
      out[k] = fixNg(translated ?? String(v));
    }
  }
  return out;
}

const translations = new Map();
const districtTranslations = new Map();

for (const line of md.split('\n')) {
  if (!line.startsWith('| `')) continue;
  const m = line.match(/^\| `([^`]+)` \|/);
  if (!m) continue;
  const key = m[1];
  const cols = line.split('|').map((c) => c.trim());
  const yours = cols[5] ?? '';
  if (yours) translations.set(key, yours);
}

let inDistricts = false;
for (const line of md.split('\n')) {
  if (line.startsWith('## Районы')) {
    inDistricts = true;
    continue;
  }
  if (!inDistricts || !line.startsWith('|')) continue;
  if (line.includes('RU') && line.includes('Ваш перевод')) continue;
  const cols = line.split('|').map((c) => c.trim());
  if (cols.length < 3) continue;
  const ruName = cols[1];
  const yours = cols[2];
  if (!ruName || ruName === 'RU' || ruName.startsWith('-') || !yours) continue;
  districtTranslations.set(ruName, fixNg(yours));
}

const alt = buildLocale(translations, ru);
alt.locale = { ru: 'RU', en: 'EN', alt: 'ALT' };

if (districtTranslations.size > 0) {
  alt.districts = Object.fromEntries(districtTranslations);
  const districtRu = Object.fromEntries(
    [...districtTranslations.keys()].map((name) => [name, name]),
  );
  const en = JSON.parse(fs.readFileSync(enPath, 'utf8'));
  ru.districts = districtRu;
  en.districts = districtRu;
  fs.writeFileSync(ruPath, `${JSON.stringify(ru, null, 2)}\n`, 'utf8');
  fs.writeFileSync(enPath, `${JSON.stringify(en, null, 2)}\n`, 'utf8');
}

fs.writeFileSync(altPath, `${JSON.stringify(alt, null, 2)}\n`, 'utf8');
console.log(`Updated ${altPath}: ${translations.size} overrides, ${districtTranslations.size} districts`);
