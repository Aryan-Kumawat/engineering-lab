import { mergeText, rotatedBounds, MM_PER_PT } from './model.mjs';
const graphemes = text => typeof Intl.Segmenter === 'function' ? [...new Intl.Segmenter(undefined, { granularity: 'grapheme' }).segment(text)].map(s => s.segment) : Array.from(text);
export function wrapText(text, width, measure) {
  const lines = [];
  for (const paragraph of text.split(/\r\n|\n|\r/)) {
    if (!paragraph.trim()) { lines.push(''); continue; }
    let line = '';
    for (const word of paragraph.trim().split(/\s+/)) {
      const next = line ? line+' '+word : word;
      if (measure(next) <= width) { line = next; continue; }
      if (line) { lines.push(line); line = ''; }
      if (measure(word) <= width) { line = word; continue; }
      for (const char of graphemes(word)) {
        if (line && measure(line+char) > width) { lines.push(line); line = ''; }
        line += char;
      }
    }
    lines.push(line);
  }
  return lines;
}
export function textLayout(content, e, measure) {
  function at(size) { const lines = wrapText(content, e.width, text => measure(text, size, e.font, e.bold)); const lineHeight = size*MM_PER_PT*1.18; return { lines, fontSize: size, lineHeight, overflow: lines.length*lineHeight > e.height + 1e-6 || lines.some(line => measure(line,size,e.font,e.bold) > e.width + 1e-6) }; }
  const original = at(e.fontSize);
  if (!original.overflow || !e.shrink) return original;
  let low = Math.ceil(e.minFontSize*2), high = Math.floor(e.fontSize*2), best = null;
  while (low <= high) { const mid = Math.floor((low+high)/2), candidate = at(mid/2); if (candidate.overflow) high = mid-1; else { best = candidate; low = mid+1; } }
  return best || at(e.minFontSize);
}
export function inspectRow(project, row, measure) {
  const issues = []; const add = (level, element, message) => issues.push({ level, elementId: element.id, elementName: element.name, message });
  for (const e of project.template.elements) {
    const bounds = rotatedBounds(e), t = project.template;
    if (bounds.minX < -.01 || bounds.minY < -.01 || bounds.maxX > t.width+.01 || bounds.maxY > t.height+.01) add('warning', e, 'Layer extends outside the page and will be clipped');
    if (e.type === 'text' || e.type === 'qr') {
      const content = mergeText(e.type === 'text' ? e.text : e.value, row);
      for (const key of content.missing) add('error', e, `Missing value: ${key}`);
      if (e.type === 'text') {
        const layout = textLayout(content.value, e, measure);
        if (layout.overflow) add('error', e, `Text overflows even at ${layout.fontSize} pt`);
        else if (layout.fontSize < e.fontSize) add('warning', e, `Text shrunk from ${e.fontSize} to ${layout.fontSize} pt`);
      } else {
        if (!content.value) add('error', e, 'QR content is empty');
        if (new TextEncoder().encode(content.value).length > 512) add('error', e, 'QR content exceeds 512 UTF-8 bytes');
        if (Math.abs(e.width-e.height) > .1) add('warning', e, 'QR is fitted into a square within this frame');
      }
    } else if (e.type === 'image') {
      const content = mergeText(e.source, row);
      for (const key of content.missing) add('error', e, `Missing image field: ${key}`);
      if (!project.assets.some(a => a.id === content.value || a.name === content.value)) add('error', e, `Image not found: ${content.value || '(none selected)'}`);
    }
  }
  return issues;
}
