const common = { rotation: 0, locked: false };
const shape = (id,x,y,width,height,fill,type='rect') => ({ ...common,id,name:id.replaceAll('-',' '),type,x,y,width,height,fill,stroke:fill,strokeWidth:0 });
const text = (id,x,y,width,height,value,fontSize,color='#172224',font='Arial',bold=false,align='left') => ({ ...common,id,name:id.replaceAll('-',' '),type:'text',x,y,width,height,text:value,fontSize,minFontSize:Math.min(8,fontSize),font,color,bold,align,shrink:true });
const qr = (id,x,y,size,value) => ({ ...common,id,name:'Check-in QR',type:'qr',x,y,width:size,height:size,value,color:'#172224',background:'#ffffff' });
export const demoData = {
  headers:['name','role','event','date','venue','code','offer'],
  rows:[
    {name:'Aryan Kumawat',role:'DESIGN CREW',event:'Design After Dark',date:'21 NOV · 6 PM',venue:'THE STUDIO / JAIPUR',code:'DAD-001',offer:'ONE GOOD COFFEE'},
    {name:'Meera Shah',role:'SPEAKER',event:'Design After Dark',date:'21 NOV · 6 PM',venue:'THE STUDIO / JAIPUR',code:'DAD-002',offer:'ONE GOOD COFFEE'},
    {name:'Rohan Patel',role:'VOLUNTEER',event:'Design After Dark',date:'21 NOV · 6 PM',venue:'THE STUDIO / JAIPUR',code:'DAD-003',offer:'ONE GOOD COFFEE'},
    {name:'Aanya Rao',role:'EVENT LEAD',event:'Design After Dark',date:'21 NOV · 6 PM',venue:'THE STUDIO / JAIPUR',code:'DAD-004',offer:'ONE GOOD COFFEE'}
  ]
};
export function preset(kind='badge') {
  let template;
  if (kind==='poster') template={width:210,height:297,background:'#f3efe5',elements:[
    text('series',14,13,180,9,'THE AFTER HOURS SERIES / 001',11,'#31483f','Courier New',true),
    shape('accent-bar',14,30,182,3,'#172224'),
    text('event-title',12,44,185,68,'{{event}}',78,'#172224','Arial',true),
    text('tagline',15,119,160,24,'GOOD IDEAS.\nBETTER COMPANY.',23,'#31483f','Courier New',true),
    shape('circle',119,156,68,68,'#d7eb67','ellipse'),shape('square',21,170,70,48,'#304b42'),
    shape('little-circle',66,155,24,24,'#e99370','ellipse'),
    text('invitation',15,238,180,15,'A NIGHT FOR PEOPLE WHO MAKE THINGS.',14,'#172224','Arial',true),
    shape('footer-rule',15,260,180,.5,'#172224'),text('date',15,267,85,9,'{{date}}',12,'#172224','Courier New',true),
    text('venue',103,267,92,9,'{{venue}}',10,'#172224','Courier New',false,'right')
  ]};
  else if (kind==='coupon') template={width:90,height:70,background:'#f7f3e9',elements:[
    shape('header-band',0,0,90,11,'#263f36'),text('brand',5,3,80,7,'COMMON TABLE / EVENT COUPON',8,'#ffffff','Courier New',true),
    text('offer',5,18,59,18,'{{offer}}',23,'#263f36','Arial',true),
    text('event',5,39,78,9,'{{event}}',10,'#263f36','Arial',true),
    shape('rule',5,50,80,.5,'#9cad9a'),text('code',5,55,55,8,'{{code}}',11,'#263f36','Courier New',true),qr('code-qr',67,52,13,'{{code}}')
  ]};
  else template={width:86,height:54,background:'#172224',elements:[
    shape('accent-band',0,0,86,8,'#d7eb67'),text('badge-label',5,2,76,5,'AFTER HOURS / CREW ACCESS',7.5,'#172224','Courier New',true),
    text('name',5,15,76,11,'{{name}}',23,'#f7f3e9','Arial',true),
    text('role',5,30,55,7,'{{role}}',10,'#d7eb67','Courier New',true),
    text('event',5,43,53,6,'{{event}}',8,'#c3d1cb','Arial'),qr('code-qr',65,32,16,'{{code}}')
  ]};
  return {version:1,name:({badge:'After Hours / Crew Badge',poster:'After Hours / Event Poster',coupon:'Common Table / Coupon'})[kind]||'After Hours / Crew Badge',template,data:structuredClone(demoData),assets:[]};
}
