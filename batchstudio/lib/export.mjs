import { zipSync, strToU8 } from 'fflate';
import { PDFDocument, rgb } from 'pdf-lib';
import { LIMITS,safeFilename,sheetLayout } from './model.mjs';
import { renderProject,canvasPNG,preflight } from './render.mjs';
const MM_TO_PT=72/25.4;
export function downloadBlob(blob,name) {
  const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),2000);
}
export async function exportBatch(project,{format='zip',dpi=180,from=0,to=project.data.rows.length-1,skipErrors=false,sheet='design',margin=10,gutter=4,cropMarks=true}={},onProgress,signal) {
  if(!['png','zip','pdf'].includes(format))throw new Error('Unknown export format');
  if(!['design','a4','letter'].includes(sheet))throw new Error('Unknown paper size');
  if(format==='pdf' && sheet!=='design' && cropMarks && (margin<3 || gutter<3))throw new Error('Crop marks require at least 3 mm margin and gutter, or turn crop marks off');
  if(!Number.isInteger(from)||!Number.isInteger(to)||from<0||to<from||to>=project.data.rows.length)throw new Error('Choose a valid record range');
  const source=project.data.rows.slice(from,to+1);
  if(source.length>LIMITS.exportRows)throw new Error('Export at most 100 records at a time; choose a smaller range');
  if(![96,150,180,300].includes(dpi))throw new Error('Choose 96, 150, 180 or 300 DPI');
  const reports=await preflight(project,source),chosen=reports.filter(r=>r.ready||!skipErrors);
  if(!skipErrors && reports.some(r=>!r.ready))throw new Error('Resolve preflight errors, or explicitly choose to skip records with errors');
  const ready=chosen.filter(r=>r.ready);
  if(!ready.length)throw new Error('No exportable records in this range');
  if(format==='png'&&ready.length!==1)throw new Error('PNG export supports one record; use ZIP for a batch');
  const t=project.template,pdf=format==='pdf'?await PDFDocument.create():null;
  const paper=sheet==='letter'?{width:215.9,height:279.4}:{width:210,height:297};
  const layout=sheet==='design'?null:sheetLayout(t.width,t.height,{pageWidth:paper.width,pageHeight:paper.height,margin,gutter});
  const files={};let pngBlob,totalBytes=0,page;
  const manifest={application:'BatchStudio',version:1,dpi,template_mm:{width:t.width,height:t.height},exported_records:[],skipped_records:reports.filter(r=>!r.ready).map(r=>r.index+from+1)};
  for(let i=0;i<ready.length;i++) {
    if(signal?.aborted)throw new Error('Export cancelled');
    const item=ready[i],row=source[item.index],recordIndex=from+item.index;
    const canvas=document.createElement('canvas');await renderProject(canvas,project,row,dpi);pngBlob=await canvasPNG(canvas);
    const bytes=new Uint8Array(await pngBlob.arrayBuffer());totalBytes+=bytes.length;
    if(totalBytes>100000000)throw new Error('Batch exceeds 100 MB of rendered images; use a smaller range or lower DPI');
    const name=`${String(recordIndex+1).padStart(3,'0')}-${safeFilename(row.name||row.code||project.name)}.png`;
    manifest.exported_records.push({record:recordIndex+1,file:name,warnings:item.issues.filter(x=>x.level==='warning').map(x=>x.message)});
    if(format==='pdf') {
      if(!layout || i%layout.perPage===0)page=pdf.addPage((layout?[paper.width,paper.height]:[t.width,t.height]).map(v=>v*MM_TO_PT));
      const position=layout?layout.positions[i%layout.perPage]:{x:0,y:0},pageHeight=layout?paper.height:t.height;
      const image=await pdf.embedPng(bytes),x=position.x*MM_TO_PT,y=(pageHeight-position.y-t.height)*MM_TO_PT,w=t.width*MM_TO_PT,h=t.height*MM_TO_PT;
      page.drawImage(image,{x,y,width:w,height:h});
      if(layout && cropMarks){const length=2*MM_TO_PT,gap=.8*MM_TO_PT;for(const [xx,yy]of [[x,y],[x+w,y],[x,y+h],[x+w,y+h]]){const sx=xx===x?-1:1,sy=yy===y?-1:1;page.drawLine({start:{x:xx+sx*gap,y:yy},end:{x:xx+sx*(gap+length),y:yy},thickness:.3,color:rgb(.25,.25,.25)});page.drawLine({start:{x:xx,y:yy+sy*gap},end:{x:xx,y:yy+sy*(gap+length)},thickness:.3,color:rgb(.25,.25,.25)});}}
    } else if(format==='zip')files[name]=bytes;
    canvas.width=1;canvas.height=1;
    onProgress?.((i+1)/ready.length);await new Promise(r=>setTimeout(r,0));
  }
  if(signal?.aborted)throw new Error('Export cancelled');
  if(format==='pdf')return {blob:new Blob([await pdf.save()],{type:'application/pdf'}),filename:safeFilename(project.name)+'.pdf',manifest};
  if(format==='png')return {blob:pngBlob,filename:manifest.exported_records[0].file,manifest};
  files['manifest.json']=strToU8(JSON.stringify(manifest,null,2));
  return {blob:new Blob([zipSync(files,{level:0})],{type:'application/zip'}),filename:safeFilename(project.name)+'.zip',manifest};
}
