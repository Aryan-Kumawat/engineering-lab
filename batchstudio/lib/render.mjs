import QRCode from 'qrcode';
import { MM_PER_PT, mergeText, LIMITS } from './model.mjs';
import { textLayout, inspectRow } from './layout.mjs';
const imageCache = new Map(), qrCache = new Map();
export function fontString(size, family, bold) { return `${bold ? '700' : '400'} ${size*MM_PER_PT}px "${family}"`; }
export function measurementContext() {
  const context = document.createElement('canvas').getContext('2d');
  return (text,size,family,bold) => { context.font = fontString(size,family,bold); return context.measureText(text).width; };
}
function imageFromData(data) {
  if (imageCache.size > 220) imageCache.delete(imageCache.keys().next().value);
  if (!imageCache.has(data)) imageCache.set(data,new Promise((resolve,reject) => { const image = new Image(); image.onload=()=>resolve(image); image.onerror=()=>reject(new Error('Image could not be decoded')); image.src=data; }));
  return imageCache.get(data);
}
export function clearImageCache() { imageCache.clear(); qrCache.clear(); }
export async function decodeImageAsset(asset) { const image=await imageFromData(asset.data);if(image.width*image.height>25000000)throw new Error('Image exceeds 25 megapixels');return image; }
async function qrImage(text,color,background,pixels) {
  const key=JSON.stringify([text,color,background,pixels]);
  if (!qrCache.has(key)) {
    if (qrCache.size>300) qrCache.clear();
    qrCache.set(key,QRCode.toDataURL(text,{errorCorrectionLevel:'M',margin:4,width:pixels,color:{dark:color,light:background}}).then(imageFromData));
  }
  return qrCache.get(key);
}
export async function renderProject(canvas,project,row,dpi=150,{guides=false}={}) {
  const t=project.template, factor=dpi/25.4, width=Math.round(t.width*factor), height=Math.round(t.height*factor);
  if (width*height>LIMITS.exportPixels) throw new Error('Image exceeds 20 megapixels; choose a lower export DPI');
  canvas.width=width;canvas.height=height;
  const ctx=canvas.getContext('2d');ctx.scale(width/t.width,height/t.height);ctx.fillStyle=t.background;ctx.fillRect(0,0,t.width,t.height);
  const measure=measurementContext();
  for (const e of t.elements) {
    ctx.save();ctx.translate(e.x+e.width/2,e.y+e.height/2);ctx.rotate(e.rotation*Math.PI/180);ctx.translate(-e.width/2,-e.height/2);
    ctx.beginPath();ctx.rect(0,0,e.width,e.height);ctx.clip();
    if (e.type==='rect' || e.type==='ellipse') {
      ctx.fillStyle=e.fill;ctx.strokeStyle=e.stroke;ctx.lineWidth=e.strokeWidth;
      if (e.type==='ellipse') {ctx.beginPath();ctx.ellipse(e.width/2,e.height/2,Math.max(.001,e.width/2-e.strokeWidth/2),Math.max(.001,e.height/2-e.strokeWidth/2),0,0,Math.PI*2);ctx.fill();if(e.strokeWidth)ctx.stroke();}
      else {ctx.fillRect(0,0,e.width,e.height);if(e.strokeWidth)ctx.strokeRect(e.strokeWidth/2,e.strokeWidth/2,e.width-e.strokeWidth,e.height-e.strokeWidth);}
    } else if(e.type==='text') {
      const content=mergeText(e.text,row).value,layout=textLayout(content,e,measure);
      ctx.font=fontString(layout.fontSize,e.font,e.bold);ctx.textBaseline='top';ctx.textAlign=e.align;ctx.fillStyle=e.color;
      const x=e.align==='center'?e.width/2:e.align==='right'?e.width:0;
      layout.lines.forEach((line,index)=>ctx.fillText(line,x,index*layout.lineHeight));
    } else if(e.type==='image') {
      const source=mergeText(e.source,row).value,asset=project.assets.find(a=>a.id===source||a.name===source);
      if(asset) {
        try {const image=await decodeImageAsset(asset),scale=e.fit==='cover'?Math.max(e.width/image.width,e.height/image.height):Math.min(e.width/image.width,e.height/image.height);ctx.drawImage(image,(e.width-image.width*scale)/2,(e.height-image.height*scale)/2,image.width*scale,image.height*scale);} catch {if(guides){ctx.fillStyle='#f6d7d1';ctx.fillRect(0,0,e.width,e.height);}}
      } else if(guides) {ctx.fillStyle='#e4e8e2';ctx.fillRect(0,0,e.width,e.height);ctx.strokeStyle='#9aa89f';ctx.lineWidth=.3;ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(e.width,e.height);ctx.moveTo(e.width,0);ctx.lineTo(0,e.height);ctx.stroke();}
    } else {
      const value=mergeText(e.value,row).value;
      if(value && new TextEncoder().encode(value).length<=512){const size=Math.min(e.width,e.height),image=await qrImage(value,e.color,e.background,Math.max(256,Math.ceil(size*factor)));ctx.imageSmoothingEnabled=false;ctx.drawImage(image,(e.width-size)/2,(e.height-size)/2,size,size);}
    }
    ctx.restore();
  }
  return canvas;
}
export async function preflight(project,rows=project.data.rows,onProgress) {
  const measure=measurementContext(),broken=new Set();
  for(const asset of project.assets)try{await decodeImageAsset(asset);}catch{broken.add(asset.id);}
  const reports=[];
  for(let index=0;index<rows.length;index++) {
    const row=rows[index],issues=inspectRow(project,row,measure);
    for(const e of project.template.elements.filter(e=>e.type==='image')){
      const source=mergeText(e.source,row).value,asset=project.assets.find(a=>a.id===source||a.name===source);
      if(asset && broken.has(asset.id))issues.push({level:'error',elementId:e.id,elementName:e.name,message:'Image cannot be decoded'});
    }
    reports.push({index,issues,ready:!issues.some(i=>i.level==='error')});
    if(index%20===0){onProgress?.(index/Math.max(1,rows.length));await new Promise(r=>setTimeout(r,0));}
  }
  return reports;
}
export function canvasPNG(canvas) {return new Promise((resolve,reject)=>canvas.toBlob(blob=>blob?resolve(blob):reject(new Error('PNG encoding failed')),'image/png'));}
