// Set globalThis.galleryBenchmark with the label, base URL and output folder before running.
const {label,base,out:to,coldOnly=false}=globalThis.galleryBenchmark;
const t=await taskSpace('xiaosang AI图集线上性能');
const p=t.page('p1');
const fs=await import('node:fs/promises');
const network={offline:false,latency:150,downloadThroughput:200000,uploadThroughput:93750,connectionType:'cellular4g'};
const viewport={width:390,height:844,deviceScaleFactor:2,mobile:true};
const windowMs=6500;
const release=await fetch(new URL('release.json',base)).then(r=>{
  if(!r.ok)throw Error('release.json: '+r.status);
  return r.json();
});
await p.cdp('Network.enable');
await p.cdp('Network.emulateNetworkConditions',network);
await p.cdp('Emulation.setCPUThrottlingRate',{rate:4});
await p.cdp('Emulation.setDeviceMetricsOverride',viewport);
const inject=await p.cdp('Page.addScriptToEvaluateOnNewDocument',{source:`
  window.perfGallery={lcp:null,fcp:null,shifts:[],longtasks:[]};
  for(const type of ['largest-contentful-paint','paint','layout-shift','longtask'])new PerformanceObserver(list=>{
    for(const e of list.getEntries()){
      if(type==='largest-contentful-paint')perfGallery.lcp={time:e.startTime,url:e.url};
      if(e.name==='first-contentful-paint')perfGallery.fcp=e.startTime;
      if(type==='longtask')perfGallery.longtasks.push({time:e.startTime,duration:e.duration});
      if(type==='layout-shift'&&!e.hadRecentInput)perfGallery.shifts.push({time:e.startTime,value:e.value});
    }
  }).observe({type,buffered:true});
`});
const nav=async url=>{
  await p.goto(url,{timeout:22000});
  await p.waitForSelector('#masonry .art-card[data-work=woodcut-mountain]');
};
const snap=()=>p.evaluate(at=>{
 const navigation=performance.getEntriesByType('navigation')[0];
 const rows=performance.getEntriesByType('resource').filter(e=>e.responseEnd<=at);
 const same=rows.filter(e=>new URL(e.name).origin===location.origin);
 const imgs=same.filter(e=>/\.(?:avif|webp|jpeg|jpg|png)(?:$|[?#])/.test(e.name));
 const positions=[...document.querySelectorAll('#masonry img')].filter(e=>e.getBoundingClientRect().top<innerHeight);
 const urlMap=new Map(imgs.map(e=>[e.name,e]));
 const data=e=>({url:e.name,start:e.startTime,end:e.responseEnd,transfer:e.transferSize,encoded:e.encodedBodySize,proto:e.nextHopProtocol,initiator:e.initiatorType});
 return {
   fcp:perfGallery.fcp,lcp:perfGallery.lcp,
   cls:perfGallery.shifts.filter(e=>e.time<=at).reduce((n,e)=>n+e.value,0),
   tbt:perfGallery.longtasks.filter(e=>e.time>=perfGallery.fcp&&e.time<=at).reduce((n,e)=>n+Math.max(0,e.duration-50),0),
   ttfb:navigation.responseStart,domReady:navigation.domContentLoadedEventEnd,
   seen:positions.length,shown:positions.filter(i=>i.complete&&i.naturalWidth).length,
   thumbsReady:positions.length&&positions.every(i=>urlMap.has(i.currentSrc))?Math.max(...positions.map(i=>urlMap.get(i.currentSrc).responseEnd)):null,
   totalRequests:rows.length+1,firstPartyRequests:same.length+1,thirdParty:rows.length-same.length,
   bytes:same.reduce((sum,e)=>sum+e.transferSize,navigation.transferSize),
   htmlTransfer:navigation.transferSize,images:imgs.length,imageBytes:imgs.reduce((sum,e)=>sum+e.transferSize,0),
   offscreen:imgs.filter(e=>!positions.some(i=>i.currentSrc===e.name)).length,
   originalRequests:same.filter(e=>/\/originals\//.test(e.name)).length,
   navigation: data(navigation),resources:rows.map(data)
 };
},windowMs);
const detail=async()=>{
 await p.evaluate(()=>{
   window.galleryTime=new Promise((resolve,reject)=>{
     const viewer=document.querySelector('#viewer');
     const point=performance.now();
     let preview=null;
     const finish=()=>{
       if(!viewer.open)return;
       const low=viewer.querySelector('.slide-low');
       if(preview===null&&low?.complete&&low?.naturalWidth)preview=performance.now()-point;
       if(viewer.querySelector('.slide-art[data-loaded]')){
         const at=performance.now()-point;
         const high=viewer.querySelector('.slide-high');
         const e=performance.getEntriesByName(high.currentSrc).at(-1);
         clearTimeout(timeout);obs.disconnect();viewer.removeEventListener('load',finish,true);
         resolve({ready:at,preview,resource:e?{url:e.name,start:e.startTime-point,end:e.responseEnd-point,transfer:e.transferSize,encoded:e.encodedBodySize}:null});
       }
     };
     const timeout=setTimeout(()=>{obs.disconnect();viewer.removeEventListener('load',finish,true);reject(Error('Detail deadline'));},18000);
     const obs=new MutationObserver(finish);
     obs.observe(viewer,{subtree:true,childList:true,attributes:true,attributeFilter:['open','data-loaded']});
     viewer.addEventListener('load',finish,true);
     document.querySelector('.art-card[data-work=woodcut-mountain]').click();
   });
 });
 await p.waitForSelector('.slide-art[data-loaded]',{timeout:20000});
 return p.evaluate(()=>window.galleryTime);
};
const runs={cold:[],warm:[]};
for(const mode of coldOnly?['cold']:['cold','warm']){
 const cold=mode==='cold';
 await p.cdp('Network.setCacheDisabled',{cacheDisabled:cold});
 const url=base+'?bench='+label+(cold?'':'-warm');
 if(!cold){
   await nav(url);
   await p.waitForFunction(()=>performance.now()>=6500);
   await detail();
 }
 for(let i=0;i<3;i++){
   await nav(url+(cold?'&n='+i:''));
   await p.waitForFunction(()=>performance.now()>=6500,undefined,{timeout:21000});
   const first=await snap();
   if(!first.lcp||!first.fcp||first.originalRequests)throw Error('Incomplete or polluted first visit');
   const image=await detail();
   runs[mode].push({first,image});
   console.log(JSON.stringify({label,mode,run:i+1,ttfb:first.ttfb,fcp:first.fcp,lcp:first.lcp.time,bytes:first.bytes,requests:first.totalRequests,thumbs:first.thumbsReady,detail:image.ready}));
 }
}
await fs.mkdir(to,{recursive:true});
await fs.writeFile(to+'/'+label+'.json',JSON.stringify({label,base,release,network,viewport,cpu:4,windowMs,runs},null,2)+'\n');
await p.cdp('Page.removeScriptToEvaluateOnNewDocument',inject);
