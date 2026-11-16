const t=await taskSpace("xiaosang AI图集加载复测");
const p=t.page("p1");
const targets=[["baseline","http://127.0.0.1:8746/gallery-baseline/"],["optimized","http://127.0.0.1:8746/gallery/"]];
const out="/tmp/xiaosang-gallery-benchmark/";
console.log({spaceId:t.spaceId});
await p.cdp("Network.enable");
await p.cdp("Network.setCacheDisabled",{cacheDisabled:true});
await p.cdp("Network.emulateNetworkConditions",{offline:false,latency:150,downloadThroughput:200000,uploadThroughput:93750,connectionType:"cellular4g"});
await p.cdp("Emulation.setCPUThrottlingRate",{rate:4});
await p.cdp("Emulation.setDeviceMetricsOverride",{width:390,height:844,deviceScaleFactor:2,mobile:true});
await p.cdp("Page.addScriptToEvaluateOnNewDocument",{source:`
window.galleryPerf={lcp:null,fcp:null,shifts:[],longtasks:[]};
for(const type of ['largest-contentful-paint','paint','layout-shift','longtask']) new PerformanceObserver(list=>{
 for(const e of list.getEntries()){
  if(type==='largest-contentful-paint') galleryPerf.lcp={time:e.startTime,url:e.url,tag:e.element?.tagName};
  if(e.name==='first-contentful-paint') galleryPerf.fcp=e.startTime;
  if(type==='longtask') galleryPerf.longtasks.push({time:e.startTime,duration:e.duration});
  if(type==='layout-shift'&&!e.hadRecentInput) galleryPerf.shifts.push({time:e.startTime,value:e.value});
 }
}).observe({type,buffered:true});
`});
const fs=await import('node:fs/promises');
await fs.mkdir(out,{recursive:true});
for(const [name,target] of targets){
const runs=[];
for(let index=0;index<3;index++){
 await p.goto(target+'?bench='+(index+1),{timeout:20000});
 await p.waitForSelector('#masonry .art-card');
 await p.waitForFunction(()=>performance.now()>=6500,undefined,{timeout:18000});
 const first=await p.evaluate(()=>{
  const at=6500;
  const nav=performance.getEntriesByType("navigation")[0];
  const entries=performance.getEntriesByType("resource").filter(e=>e.responseEnd<=at);
  const imgs=entries.filter(e=>e.initiatorType==='img'||/\.(avif|webp|png|jpe?g)(?:$|[?#])/.test(e.name));
  const positions=[...document.querySelectorAll('#masonry img')].filter(e=>e.getBoundingClientRect().top<innerHeight);
  const srcMap=new Map(imgs.map(e=>[e.name,e]));
  const below=imgs.filter(e=>!positions.some(img=>img.currentSrc===e.name));
  return {...galleryPerf,cls:galleryPerf.shifts.filter(x=>x.time<=at).reduce((sum,x)=>sum+x.value,0),tbt:galleryPerf.longtasks.filter(x=>x.time>=galleryPerf.fcp&&x.time<=at).reduce((n,x)=>n+Math.max(0,x.duration-50),0),
   requests:entries.length+1,bytes:entries.reduce((sum,e)=>sum+e.transferSize,nav.transferSize),images:imgs.length,imageBytes:imgs.reduce((sum,e)=>sum+e.transferSize,0),
   offscreenImages:below.length,seen:positions.length,shown:positions.filter(e=>e.complete&&e.naturalWidth).length,dom:document.querySelectorAll('*').length,
   thumbsReady:positions.length&&positions.every(img=>srcMap.has(img.currentSrc))? Math.max(...positions.map(img=>srcMap.get(img.currentSrc).responseEnd)):null,
   detailRequests:entries.filter(e=>/originals\/|-detail\./.test(e.name)).length};
 });
 await p.evaluate(()=>{
  const work=document.querySelector('[data-work="woodcut-mountain"]');
  window.galleryDetailStart=performance.now();
  work.click();
 });
 await p.waitForSelector('.slide-art[data-loaded]',{timeout:18000});
 const detail=await p.evaluate(()=>{
  const e=performance.getEntriesByType('resource').findLast(e=>/-detail\./.test(e.name));
  return {observedReady:performance.now()-galleryDetailStart,transfer:e?.transferSize??null,resourceEnd:e?e.responseEnd-galleryDetailStart:null};
 });
 runs.push({first,detail});
 console.log(JSON.stringify({name,run:index+1,first,detail}));
}
await fs.writeFile(out+name+".json",JSON.stringify({target,network:{latency:150,down:200000,up:93750,cpu:4},viewport:{width:390,height:844,dpr:2},windowMs:6500,runs},null,2));
}
await t.finish({keep:[]});
