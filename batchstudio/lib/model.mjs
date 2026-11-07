export const VERSION = 1;
export const FONTS = ['Arial', 'Georgia', 'Courier New', 'Verdana'];
export const TYPES = ['text', 'rect', 'ellipse', 'image', 'qr'];
export const MM_PER_PT = 25.4 / 72;
export const LIMITS = { rows: 500, columns: 40, elements: 60, assets: 12, assetBytes: 1048576, projectBytes: 25000000, exportRows: 100, exportPixels: 20000000 };
export const uid = () => globalThis.crypto.randomUUID();
const plain = value => !!value && typeof value === 'object' && !Array.isArray(value);
function string(value, name, max = 5000) { if (typeof value !== 'string' || value.length > max) throw new Error(`${name} must be text, at most ${max} characters`); return value; }
function number(value, name, min, max) { if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max) throw new Error(`${name} must be between ${min} and ${max}`); return value; }
function color(value, name) { if (!/^#[0-9a-f]{6}$/i.test(value || '')) throw new Error(`${name} must be a six-digit hex color`); return value; }
export function validateProject(project) {
  if (!plain(project) || project.version !== VERSION) throw new Error('Expected a BatchStudio version 1 project');
  string(project.name, 'Project name', 100);
  const t = project.template;
  if (!plain(t)) throw new Error('Template missing');
  number(t.width, 'Page width (mm)', 5, 1000); number(t.height, 'Page height (mm)', 5, 1000); color(t.background, 'Page background');
  if (!Array.isArray(t.elements) || t.elements.length > LIMITS.elements) throw new Error('A template supports up to 60 layers');
  const ids = new Set();
  for (const e of t.elements) {
    if (!plain(e) || !TYPES.includes(e.type)) throw new Error('Unknown layer type');
    string(e.id, 'Layer id', 80); if (!e.id || ids.has(e.id)) throw new Error('Layer IDs must be nonempty and unique'); ids.add(e.id);
    string(e.name, 'Layer name', 100);
    for (const key of ['x', 'y']) number(e[key], key, -1000, 2000);
    for (const key of ['width', 'height']) number(e[key], key, .5, 2000);
    number(e.rotation, 'Rotation', -180, 180);
    if (typeof e.locked !== 'boolean') throw new Error('Layer locked must be a boolean');
    if (e.type === 'text') {
      string(e.text, 'Text'); color(e.color, 'Text color');
      if (!FONTS.includes(e.font)) throw new Error('Unsupported font family');
      number(e.fontSize, 'Font size', 4, 200); number(e.minFontSize, 'Minimum font size', 4, e.fontSize);
      if (!['left', 'center', 'right'].includes(e.align) || typeof e.bold !== 'boolean' || typeof e.shrink !== 'boolean') throw new Error('Invalid text style');
    } else if (e.type === 'rect' || e.type === 'ellipse') {
      color(e.fill, 'Shape fill'); color(e.stroke, 'Shape stroke'); number(e.strokeWidth, 'Stroke width (mm)', 0, 20);
    } else if (e.type === 'image') {
      string(e.source, 'Image source', 200); if (!['cover', 'contain'].includes(e.fit)) throw new Error('Invalid image fit');
    } else {
      string(e.value, 'QR value'); color(e.color, 'QR color'); color(e.background, 'QR background');
    }
  }
  if (!plain(project.data) || !Array.isArray(project.data.headers) || !Array.isArray(project.data.rows)) throw new Error('Data headers and rows required');
  const { headers, rows } = project.data;
  if (headers.length > LIMITS.columns || new Set(headers).size !== headers.length) throw new Error('Use up to 40 unique CSV headers');
  for (const h of headers) { string(h, 'Column header', 80); if (!h.trim()) throw new Error('CSV headers cannot be empty'); }
  if (rows.length > LIMITS.rows) throw new Error('Data is limited to 500 records');
  for (const row of rows) {
    if (!plain(row) || Object.keys(row).length !== headers.length || Object.keys(row).some(k => !headers.includes(k))) throw new Error('Each record must match the column headers');
    for (const h of headers) string(row[h], 'Cell value');
  }
  if (!Array.isArray(project.assets) || project.assets.length > LIMITS.assets) throw new Error('Use up to 12 local images');
  const assetIds = new Set(), assetNames = new Set();
  for (const asset of project.assets) {
    if (!plain(asset)) throw new Error('Invalid image asset');
    string(asset.id, 'Asset ID', 80); string(asset.name, 'Asset filename', 200);
    if (!asset.id || assetIds.has(asset.id) || assetNames.has(asset.name)) throw new Error('Asset IDs and filenames must be unique');
    assetIds.add(asset.id); assetNames.add(asset.name);
    if (typeof asset.data !== 'string' || !/^data:image\/(png|jpeg|webp);base64,[a-z0-9+/=]+$/i.test(asset.data) || asset.data.length > 1450000) throw new Error('Images must be embedded PNG/JPEG/WebP, at most 1 MB each');
  }
  if (new TextEncoder().encode(JSON.stringify(project)).length > LIMITS.projectBytes) throw new Error('Project exceeds 25 MB');
  return project;
}
export function parseProject(text) {
  if (new TextEncoder().encode(text).length > LIMITS.projectBytes) throw new Error('Project exceeds 25 MB');
  return validateProject(JSON.parse(text));
}
export function mergeText(text, row) {
  const missing = [];
  const value = text.replace(/{{\s*([^{}]+?)\s*}}/g, (_, token) => {
    const key = token.trim(); const cell = Object.hasOwn(row, key) ? row[key] : '';
    if (cell === '') missing.push(key); return cell;
  });
  if (/{{|}}/.test(value)) missing.push('malformed placeholder');
  return { value, missing: [...new Set(missing)] };
}
export function parseCSV(input) {
  if (new TextEncoder().encode(input).length > 2000000) throw new Error('CSV exceeds 2 MB');
  if (input.includes('\0')) throw new Error('Save the CSV as UTF-8, not UTF-16');
  const text = input.replace(/^\uFEFF/, ''); const records = []; let row = [], cell = '', quoted = false, afterQuote = false;
  function finishCell() { row.push(cell); cell = ''; afterQuote = false; }
  function finishRow() { finishCell(); if (row.some(c => c !== '')) records.push(row); row = []; if (records.length > LIMITS.rows + 1) throw new Error('CSV supports up to 500 data rows'); }
  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    if (quoted) {
      if (char === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else { quoted = false; afterQuote = true; } } else cell += char;
    } else if (char === ',') finishCell();
    else if (char === '\n' || char === '\r') { if (char === '\r' && text[i + 1] === '\n') i++; finishRow(); }
    else if (char === '"') { if (cell !== '' || afterQuote) throw new Error('Unexpected quote in CSV'); quoted = true; }
    else { if (afterQuote) throw new Error('Unexpected characters after a quoted CSV cell'); cell += char; }
    if (cell.length > 5000) throw new Error('CSV cells are limited to 5,000 characters');
  }
  if (quoted) throw new Error('Unclosed quoted CSV field');
  if (cell !== '' || row.length || afterQuote) finishRow();
  if (!records.length) throw new Error('CSV must contain a header');
  const headers = records.shift().map(h => h.trim());
  if (!headers.length || headers.length > LIMITS.columns || headers.some(h => !h || h.length > 80) || new Set(headers).size !== headers.length) throw new Error('Use 1–40 nonempty, unique headers (up to 80 characters each)');
  const rows = records.map((values, i) => { if (values.length !== headers.length) throw new Error(`CSV data row ${i + 1}: expected ${headers.length} cells, got ${values.length}`); return Object.fromEntries(headers.map((h, j) => [h, values[j]])); });
  return { headers, rows };
}
export function encodeCSV(data) {
  const escape = text => /[",\r\n]/.test(text) ? '"' + text.replace(/"/g, '""') + '"' : text;
  return [data.headers, ...data.rows.map(r => data.headers.map(h => r[h]))].map(row => row.map(escape).join(',')).join('\r\n');
}
export function newElement(type, page) {
  const base = { id: uid(), name: ({ text: 'Text', rect: 'Rectangle', ellipse: 'Ellipse', image: 'Image', qr: 'QR code' })[type], type, x: page.width * .15, y: page.height * .2, width: Math.min(65, page.width * .7), height: 18, rotation: 0, locked: false };
  if (type === 'text') return { ...base, text: 'Your text', font: 'Arial', fontSize: 20, minFontSize: 8, bold: false, align: 'left', shrink: true, color: '#172224' };
  if (type === 'rect' || type === 'ellipse') return { ...base, height: 30, fill: '#d8ed63', stroke: '#172224', strokeWidth: 0 };
  if (type === 'image') return { ...base, height: 35, source: '', fit: 'cover' };
  return { ...base, width: 20, height: 20, value: '{{code}}', color: '#172224', background: '#ffffff' };
}
export function safeFilename(value) { return (value || 'design').normalize('NFKD').replace(/[^a-z0-9._-]+/gi, '-').replace(/^-+|-+$/g, '').slice(0, 70) || 'design'; }
export function rotatedBounds(e) {
  const radians = e.rotation * Math.PI / 180, c = Math.cos(radians), s = Math.sin(radians), cx = e.x + e.width / 2, cy = e.y + e.height / 2;
  const points = [[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]].map(([x,y]) => [cx + c*x*e.width - s*y*e.height, cy + s*x*e.width + c*y*e.height]);
  return { minX: Math.min(...points.map(p => p[0])), maxX: Math.max(...points.map(p => p[0])), minY: Math.min(...points.map(p => p[1])), maxY: Math.max(...points.map(p => p[1])) };
}
export function hitTest(e, x, y) {
  const a = -e.rotation * Math.PI / 180, dx = x - e.x - e.width / 2, dy = y - e.y - e.height / 2;
  return Math.abs(Math.cos(a)*dx - Math.sin(a)*dy) <= e.width/2 && Math.abs(Math.sin(a)*dx + Math.cos(a)*dy) <= e.height/2;
}
export function sheetLayout(width, height, { pageWidth = 210, pageHeight = 297, margin = 10, gutter = 4 } = {}) {
  for (const [key, value] of Object.entries({ width, height, pageWidth, pageHeight, margin, gutter })) if (!Number.isFinite(value) || value < (key === 'margin' || key === 'gutter' ? 0 : .5)) throw new Error('Invalid print sheet dimensions');
  const columns = Math.floor((pageWidth - margin*2 + gutter)/(width+gutter)), rows = Math.floor((pageHeight - margin*2 + gutter)/(height+gutter));
  if (columns < 1 || rows < 1) throw new Error('Design does not fit this sheet at actual size; choose design-sized pages or a smaller template');
  if (columns * rows > 200) throw new Error('Sheet supports at most 200 placements');
  return { columns, rows, perPage: columns*rows, positions: Array.from({ length: columns*rows }, (_, i) => ({ x: margin+(i%columns)*(width+gutter), y: margin+Math.floor(i/columns)*(height+gutter) })) };
}
