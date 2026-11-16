/* global arrangeGrid, observeThumbnails, disconnectThumbnails, thumbnailPrefetchReady */
const $ = (s, root = document) => root.querySelector(s);
const conf = JSON.parse($('#catalog-config').textContent);
conf.seeds=conf.seeds.map(unpack);
conf.meta.forEach(s=>s.cover=unpackCover(s.cover));
const previews=new Map(conf.previews.map(info=>[info[0],unpackDetail(info)]));
const series = new Map(conf.meta.map(s => [s.id,s]));
const gallery = $('#masonry'), more = $('#load-more'), sheet = $('#series-dialog');
const viewer = $('#viewer'), scroller = $('#slide-scroller');
const promptDialog = $('#prompt-dialog'), box = $('#search'), category = $('#category-select');
const storageKey='xiaosang-gallery.likes.v1';
const seedCount=conf.seeds.length, batch=16;
const buckets=new Map(), feeds=new Map(), photoToPost=new Map(), scripts=new Map();
let searchIndex=null;
let index=null, templates=null, screenPosts=conf.seeds, count=seedCount;
let filter='all', subgroup='', transition=0, searchTimer;
let displayed, columnWidth=gallery.clientWidth, likesChanged=false;
let viewPosts=[], postIndex=-1, photoIndex=0, postData=null, galleryOpener, saveScroll=0;
let viewTrack, frame=0, revision=0, gesture, swipeClickUntil=0;
let activeRendered;

function safeLikes() {
  try { const list=JSON.parse(localStorage.getItem(storageKey));return new Set(Array.isArray(list)?list:[]); }
  catch { return new Set(); }
}
const likes=safeLikes();
const escapeHTML=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const icon=name=>`<svg class="icon" aria-hidden="true"><use href="#lucide-${name}"></use></svg>`;
const nameFor=id=>id==='all'?'全部作品':id==='liked'?'已赞作品':series.get(id)?.title||'全部作品';
const $title=$('#series-title');

function unpackCover([work,w,h,mw,mh]) {
  const prefix='media/v2/'+work;
  const useMedium=w!==mw||h!==mh;
  return [work,prefix+'-s.avif',prefix+'-s.webp',w,h,
    prefix+(useMedium?'-m.avif':'-s.avif'),
    prefix+(conf.singleWebpThumb||!useMedium?'-s.webp':'-m.webp'),mw,mh];
}
function unpack([id,group,title,cat,n,bucket,work,w,h,mw,mh]) {
  return {id,group,title,cat,n,bucket,cover:unpackCover([work,w,h,mw,mh])};
}
function unpackDetail([id,title,width,height,crop,quality,original,avif=true]) {
  const prefix='media/v2/'+id;
  return {id,title,width,height,crop,quality,original,variants:{
    s:[prefix+'-s.avif',prefix+'-s.webp'],
    detail:[prefix+(avif?'-detail.avif':'-detail.webp'),prefix+'-detail.webp'],
  }};
}
window.registerBucket=(key,data)=>buckets.set(key,data);
window.registerFeed=(group,data)=>feeds.set(group,data.map(unpack));
window.registerLikes=(group,data)=>photoToPost.set(group,data);
window.registerSearch=items=>{searchIndex=new Map(items);};
window.registerTemplates=data=>{templates=data;};
window.registerIndex=items=>{index=items.map(unpack);};
function loadScript(url, priority='auto') {
  if (scripts.has(url)) return scripts.get(url);
  const promise=new Promise((resolve,reject)=>{
    const el=document.createElement('script');
    el.fetchPriority=priority;
    el.src=url;
    el.onload=resolve;
    el.onerror=()=>{el.remove();scripts.delete(url);reject(new Error(url));};
    document.head.append(el);
  });
  scripts.set(url,promise);
  return promise;
}
async function loadIndex() {
  if (!index) await loadScript('data/index.js');
  return index;
}
async function loadPost(post, priority='auto') {
  const key=post.group+'-'+post.bucket;
  if(!buckets.has(key))await loadScript('data/'+key+'.js',priority);
  const data=buckets.get(key);
  return {data,photos:data.posts[post.id]};
}
async function locateLikes(group){
  if(!photoToPost.has(group))await loadScript('data/'+group+'-likes.js');
  const map=photoToPost.get(group);
  const ids=new Set([...likes].map(id=>map[id]).filter(Boolean));
  return (await loadFeed(group)).filter(post=>ids.has(post.id));
}
async function loadFeed(id) {
  if (!feeds.has(id)) await loadScript('data/'+id+'-feed.js');
  return feeds.get(id);
}

for(const id of ['#search-label','#series-search-label']) $(id).insertAdjacentHTML('afterbegin',icon('search'));
for(const btn of document.querySelectorAll('[data-close]')) btn.innerHTML=icon(btn.dataset.close==='viewer'?'arrow-left':'x');
$('#viewer-tools summary').innerHTML=icon('ellipsis');
$('#viewer-like').innerHTML=icon('heart');
$('#viewer-download').innerHTML=icon('download');
$('#photo-prev').innerHTML=icon('chevron-left');
$('#photo-next').innerHTML=icon('chevron-right');
for(const el of document.querySelectorAll('.tools-popup a')) el.insertAdjacentHTML('beforeend',icon('arrow-up-right'));

function coverMarkup(cover,small=false) {
  const [id,sa,sw,w,h,ma,mw,w2]=cover;
  const sizes=small?'48px':'(max-width: 720px) 46vw, (max-width: 1149px) 30vw, 250px';
  const avif=small||w===w2?sa:`${sa} ${w}w, ${ma} ${w2}w`;
  const webp=small||w===w2||sw===mw?sw:`${sw} ${w}w, ${mw} ${w2}w`;
  const attrs=small?'src':'data-src';
  return `<picture><source type="image/avif" ${attrs}set="${avif}" sizes="${sizes}"><img ${attrs}="${sw}" ${attrs}set="${webp}" sizes="${sizes}" width="${w}" height="${h}" alt="" decoding="async"${small?' loading="lazy"':''}></picture>`;
}
function label(post) {
  const title=series.get(post.group).title;
  return title+(post.cat&&post.cat!==post.title?' · '+post.cat:'');
}
function card(post) {
  const multi=post.n>1?`<span class="stack-badge" aria-label="${post.n} 张图片">${icon('images')}${post.n}</span>`:'';
  return `<button class="art-card" type="button" data-post="${post.id}" data-work="${post.cover[0]}" aria-label="${escapeHTML(post.title)}"><span class="art-img">${coverMarkup(post.cover)}${multi}</span><span class="art-caption"><strong>${escapeHTML(post.title)}</strong><small>${escapeHTML(label(post))}</small></span></button>`;
}
let loadObserver=null;
function observeMore() {
  loadObserver?.disconnect();
  if (!('IntersectionObserver' in window) || !thumbnailPrefetchReady || viewer.open || document.hidden) return;
  loadObserver=new IntersectionObserver(entries=>{
    if(entries.some(e=>e.isIntersecting)) append();
  },{rootMargin:'0px 0px '+innerHeight+'px 0px'});
  if(!more.hidden)loadObserver.observe(more);
}
window.addEventListener('resize',observeMore);
window.addEventListener('load',observeMore,{once:true});
const showError=()=>{more.textContent='重试加载';more.hidden=false;};

let appending=false;
async function append() {
  if(appending||more.hidden||viewer.open||document.hidden)return;
  appending=true;
  const token=transition;
  try {
    if(filter==='all'&&!box.value.trim()&&screenPosts.length===seedCount) {
      const full=await loadIndex();
      if(token!==transition) return;
      screenPosts=full;
    }
    const next=screenPosts.slice(count,count+batch);
    if(next.length){
      gallery.insertAdjacentHTML('beforeend',next.map(card).join(''));
      arrangeGrid(gallery,count);
      count+=next.length;
      observeThumbnails(gallery);
    }
    more.hidden=count>=screenPosts.length;
    more.textContent='加载更多';
    loadObserver?.unobserve(more);
    observeMore();
  } catch {if(token===transition)showError();}
  finally {appending=false;}
}
if('ResizeObserver' in window) {
  new ResizeObserver(()=>{
    if(columnWidth!==gallery.clientWidth) {
      columnWidth=gallery.clientWidth;
      requestAnimationFrame(()=>arrangeGrid(gallery));
    }
  }).observe(gallery);
}
function syncFilters() {
  $title.textContent=nameFor(filter);
  $('#series-toggle').setAttribute('aria-label','切换系列，当前为'+nameFor(filter));
  const group=series.get(filter);
  $('#site-skills').href='skills/index.html'+(group?'#'+group.id:'');
  $('#category-row').hidden=!group||group.cats.length<2;
  category.replaceChildren(new Option('全部分组',''),...(group?.cats||[]).map(label=>new Option(label,label)));
  category.value=subgroup;
}
async function resetGrid() {
  const active=++transition;
  const query=box.value.trim().toLocaleLowerCase();
  const words=query.split(/\s+/).filter(Boolean);
  syncFilters();
  const status=$('#results-status');
  try {
    let items=filter==='all'?await loadIndex():filter==='liked'?[]:await loadFeed(filter);
    if(filter==='liked') {
      const ids=new Set([...likes].map(id=>id.includes('-')?id.split('-')[0]:'').filter(id=>series.has(id)));
      items=(await Promise.all([...ids].map(locateLikes))).flat();
    }
    if(subgroup)items=items.filter(p=>p.cat===subgroup);
    if(words.length){
      if (!searchIndex) await loadScript('data/search.js');
      items=items.filter(post=>{
        const text=(searchIndex.get(post.id)||post.title).toLocaleLowerCase();
        return words.every(word=>text.includes(word));
      });
    }
    if(active!==transition)return;
    screenPosts=items;
    status.hidden=!query;
    status.textContent=query?`${items.length} 帖`:'';
    disconnectThumbnails();
    loadObserver?.unobserve(more);
    gallery.innerHTML=items.length?'':`<div class="empty">${icon(filter==='liked'?'heart':'image-off')}<p>${filter==='liked'&&!query?'点赞的作品会出现在这里':'没有找到匹配的作品'}</p></div>`;
    count=0;
    appending=false;
    more.hidden=!items.length;
    $('#swipe-toggle').disabled=!items.length;
    if(items.length) {
      await append();
      observeMore();
    }
  } catch {
    if(active===transition) {status.hidden=false;status.textContent='数据暂时无法加载';showError();}
  }
}
function changeSeries(id) {
  filter=id;subgroup='';box.value='';
  const url=new URL(location);
  if(id==='all') url.searchParams.delete('series');
  else url.searchParams.set('series',id);
  history.replaceState(null,'',url);
  window.scrollTo(0,0);
  resetGrid();
}
function renderSeriesList() {
  const word=$('#series-search').value.trim().toLocaleLowerCase();
  const items=[{id:'all',title:'全部作品',icon:'layout-grid',works:conf.meta.reduce((n,s)=>n+s.works,0)},{id:'liked',title:'已赞作品',icon:'heart',works:likes.size},...conf.meta].filter(s=>s.title.toLocaleLowerCase().includes(word));
  $('#series-list').innerHTML=items.map(s=>`<button type="button" class="series-option" data-series="${s.id}" aria-pressed="${filter===s.id}"><span class="series-cover">${s.icon?icon(s.icon):coverMarkup(s.cover,true)}</span><strong>${escapeHTML(s.title)}</strong><small>${s.works} 张</small></button>`).join('')||'<p class="empty">没有匹配的系列</p>';
}
function discloseSearch(show) {
  $('#search-row').hidden=!show;
  $('#search-toggle').setAttribute('aria-expanded',String(show));
  (show?box:$('#search-toggle')).focus({preventScroll:true});
}
function localLike(id) {
  if(likes.has(id))likes.delete(id);else likes.add(id);
  try{localStorage.setItem(storageKey,JSON.stringify([...likes]));}catch{}
  likesChanged=true;
  syncLike(id);
}
function syncLike(id) {
  const button=$('#viewer-like');
  const selected=likes.has(id);
  button.setAttribute('aria-pressed',String(selected));
  button.setAttribute('aria-label',selected?'取消点赞':'点赞');
  button.title=selected?'取消点赞':'点赞';
  button.disabled=!id;
}
function imageCount(post) {
  const counter=$('#viewer-index');
  const total=filter==='all'&&!box.value.trim()?conf.count:viewPosts.length;
  counter.textContent=post.n>1?`${photoIndex+1} / ${post.n}`:`${postIndex+1} / ${total}`;
  const prev=$('#photo-prev'), next=$('#photo-next');
  prev.hidden=next.hidden=post.n<=1;
  prev.disabled=photoIndex===0;
  next.disabled=photoIndex>=post.n-1;
}
const warmedPhotos=new Map();
let upcomingTimer, upcomingQueue=[], warmingPhoto=false;

function upcomingLimit() {
  const connection=navigator.connection;
  if(document.hidden||navigator.onLine===false||connection?.saveData||['slow-2g','2g'].includes(connection?.effectiveType))return 0;
  return connection?.effectiveType==='3g'?1:3;
}
function stopUpcomingPhotos() {
  clearTimeout(upcomingTimer);
  upcomingQueue=[];
}
function warmPhoto(work) {
  const url=work.variants.detail[0];
  if(warmedPhotos.has(url))return warmedPhotos.get(url).ready;
  const image=new Image();
  image.fetchPriority='low';
  image.decoding='async';
  const entry={image,ready:null};
  entry.ready=new Promise(resolve=>{
    const finish=success=>{
      clearTimeout(timeout);
      image.onload=image.onerror=null;
      if(!success&&warmedPhotos.get(url)===entry)warmedPhotos.delete(url);
      resolve();
    };
    const timeout=setTimeout(()=>{image.removeAttribute('src');finish(false);},15000);
    image.onerror=()=>finish(false);
    image.onload=()=>{
      if(image.decode)image.decode().then(()=>finish(true),()=>finish(false));
      else finish(true);
    };
    image.src=url;
  });
  warmedPhotos.set(url,entry);
  if(warmedPhotos.size>6)warmedPhotos.delete(warmedPhotos.keys().next().value);
  return entry.ready;
}
async function warmQueue() {
  if(warmingPhoto)return;
  warmingPhoto=true;
  try {
    while(upcomingQueue.length&&viewer.open&&upcomingLimit()) {
      await warmPhoto(upcomingQueue.shift());
    }
  } finally {warmingPhoto=false;}
}
function scheduleUpcomingPhotos() {
  stopUpcomingPhotos();
  const limit=upcomingLimit();
  if(!viewer.open||!limit)return;
  const token=revision;
  const current=viewPosts[postIndex], next=viewPosts[postIndex+1];
  const currentPhoto=photoIndex;
  upcomingTimer=setTimeout(async()=>{
    const valid=()=>token===revision&&viewer.open&&upcomingLimit()>0;
    try {
      if(current.n>currentPhoto+1) {
        const full=postData||await loadPost(current,'low');
        if(!valid())return;
        postData=full;
        upcomingQueue=full.photos.slice(currentPhoto+1,currentPhoto+1+limit).map(id=>full.data.photos[id]);
        warmQueue();
      }
      // Warm the next post's cover as well for vertical swiping.
      if(next&&limit>1) {
        const full=await loadPost(next,'low');
        if(!valid())return;
        upcomingQueue.push(full.data.photos[full.photos[0]]);
        warmQueue();
      }
    } catch { /* The current artwork stays usable if speculative metadata fails. */ }
  },180);
}
document.addEventListener('visibilitychange',()=>{
  if(document.hidden) {
    stopUpcomingPhotos();
    disconnectThumbnails();
    loadObserver?.disconnect();
  } else {
    observeThumbnails(gallery);
    observeMore();
    if(viewer.open&&viewer.querySelector('.slide-art[data-loaded]'))scheduleUpcomingPhotos();
  }
});
navigator.connection?.addEventListener('change',()=>{
  stopUpcomingPhotos();
  if(viewer.open&&viewer.querySelector('.slide-art[data-loaded]'))scheduleUpcomingPhotos();
});

function fillSlide(slide,work,thumb) {
  const [x,y,w,h]=work.crop;
  slide.innerHTML='<div class="slide-area"><div class="slide-art"><img class="slide-low" alt="" draggable="false"><img class="slide-high" alt="" draggable="false"></div></div>';
  const art=$('.slide-art',slide);
  art.style.setProperty('--ratio',work.width/work.height);
  art.style.setProperty('--left',100*x/work.width+'%');
  art.style.setProperty('--top',100*y/work.height+'%');
  art.style.setProperty('--width',100*w/work.width+'%');
  art.style.setProperty('--height',100*h/work.height+'%');
  art.toggleAttribute('data-paper',x>0||y>0);
  const small=$('.slide-low',art), high=$('.slide-high',art);
  if(thumb)small.src=thumb;
  else {
    small.src=work.variants.s[0];
    small.onerror=()=>{small.onerror=null;small.src=work.variants.s[1];};
  }
  const token=revision;
  high.alt=work.title;
  high.fetchPriority='high';
  const reveal=()=>{
    if(token!==revision||!viewer.open||!art.isConnected)return;
    art.setAttribute('data-loaded','');
    scheduleUpcomingPhotos();
  };
  if(!high.decode) high.addEventListener('load',reveal,{once:true});
  high.src=work.variants.detail[0];
  if(high.decode) high.decode().then(reveal).catch(()=>{
    if(token!==revision||!viewer.open||work.variants.detail[0]===work.variants.detail[1]) return;
    high.src=work.variants.detail[1];
    return high.decode().then(reveal).catch(()=>{});
  });

}
function drawPhoto(work,shortcut) {
  const post=viewPosts[postIndex];
  const slide=$('[data-slide="'+postIndex+'"]',viewTrack);
  if(!post||!slide||!work)return;
  activeRendered=work;
  fillSlide(slide,work,shortcut);
  $('#viewer-title').textContent=work.title;
  const source=$('#viewer-download');
  source.hidden=false;
  source.href=work.original;
  source.download=work.original.split('/').pop();
  const label=work.quality==='original'?'下载原图':'下载发布图';
  source.title=label;
  source.setAttribute('aria-label',label);
  syncLike(work.id);
  imageCount(post);
}
function layoutViewer() {
  const height=scroller.clientHeight;
  const length=viewPosts.length;
  viewTrack.style.height=length*height+'px';
  const nearest=[postIndex-1,postIndex,postIndex+1].filter(n=>n>=0&&n<length);
  for(const item of [...viewTrack.children]){
    if(!nearest.includes(Number(item.dataset.slide)))item.remove();
  }
  for(const index of nearest){
    let item=$('[data-slide="'+index+'"]',viewTrack);
    if(!item) {
      item=document.createElement('div');
      item.className='slide';
      item.dataset.slide=index;
      viewTrack.append(item);
    }
    item.style.height=height+'px';
    item.style.top=index*height+'px';
    if(index!==postIndex&&item.firstChild)item.replaceChildren();
  }
}
async function changePost(position,shortcut) {
  if(position<0||position>=viewPosts.length||position===postIndex)return;
  postIndex=position;
  photoIndex=0;
  postData=null;
  activeRendered=null;
  const token=++revision;
  stopUpcomingPhotos();
  layoutViewer();
  const post=viewPosts[position];
  const seriesMeta=series.get(post.group);
  if(!seriesMeta)return;
  $('#viewer-tools').open=false;
  const source=$('#viewer-download');
  source.hidden=true;
  syncLike(null);
  $('#viewer-title').textContent=post.title;
  $('#viewer-series').textContent=label(post);
  $('#viewer-skill').href='skills/index.html#'+post.group;
  $('#viewer-source').href=seriesMeta.url;
  imageCount(post);
  const cover=previews.get(post.cover[0]);
  if(cover)drawPhoto(cover,shortcut);
  if(!cover){
    const [,avif,webp,width,height]=post.cover;
    const slide=$('[data-slide="'+position+'"]',viewTrack);
    slide.innerHTML='<div class="slide-area"><div class="slide-art"></div></div>';
    const art=$('.slide-art',slide);
    art.style.setProperty('--ratio',width/height);
    const image=new Image();
    image.className='slide-low';
    image.alt='';
    image.draggable=false;
    image.onerror=()=>{image.onerror=null;image.src=webp;};
    image.src=shortcut||avif;
    art.append(image);
    try {
      const full=await loadPost(post);
      if(token!==revision||!viewer.open)return;
      postData=full;
      drawPhoto(full.data.photos[full.photos[0]],image.currentSrc||shortcut);
    } catch {
      if(token===revision) $('#viewer-title').textContent='图片暂时无法加载';
    }
  }
  if(filter==='all'&&!box.value.trim()&&postIndex>=seedCount-3&&viewPosts.length===seedCount&&conf.count>seedCount){
    const full=await loadIndex().catch(()=>null);
    if(full&&viewer.open&&viewPosts.length===seedCount){
      viewPosts=full;
      layoutViewer();
      imageCount(viewPosts[postIndex]);
    }
  }
}
async function changePhoto(position) {
  const post=viewPosts[postIndex];
  if(!post||position<0||position>=post.n||position===photoIndex)return;
  const token=++revision;
  stopUpcomingPhotos();
  try {
    if(!postData){
      const full=await loadPost(post);
      if(token!==revision||!viewer.open)return;
      postData=full;
    }
    photoIndex=position;
    drawPhoto(postData.data.photos[postData.photos[position]]);
  } catch {
    if(token===revision) $('#viewer-title').textContent='图片暂时无法加载';
  }
}

async function openViewer(post,opener) {
  if(!post)return;
  viewPosts=screenPosts;
  const start=viewPosts.indexOf(post);
  if(start<0)return;
  postIndex=-1;
  galleryOpener=opener;
  likesChanged=false;
  saveScroll=window.scrollY;
  viewTrack=document.createElement('div');
  viewTrack.className='slide-track';
  scroller.replaceChildren(viewTrack);
  disconnectThumbnails();
  loadObserver?.disconnect();
  viewer.showModal();
  const shortcut=$('img',opener)?.currentSrc;
  changePost(start,shortcut||undefined);
  scroller.scrollTop=start*scroller.clientHeight;

}
function verticalJump(target) {
  if(target<0||target>=viewPosts.length)return;
  if(Math.abs(target-postIndex)>1) changePost(target);
  scroller.scrollTo({top:target*scroller.clientHeight,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
}
scroller.addEventListener('scroll',()=>{
  if(frame)return;
  frame=requestAnimationFrame(()=>{
    frame=0;
    if(viewer.open&&scroller.clientHeight)changePost(Math.round(scroller.scrollTop/scroller.clientHeight));
  });
},{passive:true});
scroller.addEventListener('touchstart',event=>{
  if(event.touches.length===1){
    const finger=event.touches[0];
    gesture=[finger.clientX,finger.clientY];
  }else gesture=null;
},{passive:true});
scroller.addEventListener('touchend',event=>{
  if(!gesture)return;
  const finger=event.changedTouches[0];
  const x=finger.clientX-gesture[0],y=finger.clientY-gesture[1];
  gesture=null;
  if(Math.abs(x)>42&&Math.abs(x)>Math.abs(y)*1.3){
    swipeClickUntil=performance.now()+280;
    changePhoto(photoIndex+(x<0?1:-1));
  }
},{passive:true});
scroller.addEventListener('touchcancel',()=>{gesture=null;},{passive:true});
scroller.addEventListener('click',event=>{
  if(event.target.closest('.slide-art')&&performance.now()>swipeClickUntil) viewer.toggleAttribute('data-quiet');
});
viewer.addEventListener('keydown',event=>{
  if(event.target.closest('.tools'))return;
  const k=event.key;
  if(k==='h'||k==='H')viewer.toggleAttribute('data-quiet');
  if(k==='ArrowLeft'||k==='ArrowRight'){
    event.preventDefault();
    changePhoto(photoIndex+(k==='ArrowLeft'?-1:1));
  }
  if(['ArrowDown','ArrowUp','PageDown','PageUp'].includes(k)){
    event.preventDefault();
    verticalJump(postIndex+(['ArrowDown','PageDown'].includes(k)?1:-1));
  }
});
window.addEventListener('resize',()=>{
  if(viewer.open){
    layoutViewer();
    scroller.scrollTop=postIndex*scroller.clientHeight;
  }
});
viewer.addEventListener('close',()=>{
  revision++;
  stopUpcomingPhotos();
  warmedPhotos.clear();
  observeThumbnails(gallery);
  observeMore();
  if(frame)cancelAnimationFrame(frame);
  frame=0;postIndex=-1;gesture=null;
  scroller.replaceChildren();
  $('#viewer-tools').open=false;
  viewer.removeAttribute('data-quiet');
  if(likesChanged&&filter==='liked')resetGrid();
  (galleryOpener?.isConnected?galleryOpener:$('#series-toggle')).focus({preventScroll:true});
  window.scrollTo(0,saveScroll);
});

async function openPrompt(scope) {
  const post=scope==='work'?viewPosts[postIndex]:screenPosts[0]||conf.seeds.find(p=>p.group===filter)||conf.seeds[0];
  if(!post)return;
  const group=series.get(post.group);
  if(!templates){try{await loadScript('data/templates.js');}catch{return;}}
  const chosen=scope==='work'?activeRendered:null;
  $('#prompt-series').textContent=group.title;
  const tags=['主体','视角与场景','配色与材质'];
  const sample=[chosen?.title||post.title,post.cat||'合适的取景与视角',group.style];
  $('#prompt-content').innerHTML=`<div class="prompt-tabs" aria-label="提示词形式"><button type="button" data-prompt-mode="example" aria-pressed="true">填写示例</button><button type="button" data-prompt-mode="template" aria-pressed="false">通用模板</button></div>
    <div class="prompt-fields">${tags.map((tag,i)=>`<label>${tag}<input data-prompt-index="${i}" value="${escapeHTML(sample[i])}"></label>`).join('')}</div><pre id="prompt-text" tabindex="0"></pre>
    <div class="prompt-actions"><button type="button" class="primary-button" id="copy-prompt">${icon('copy')}复制 Prompt</button><a href="skills/index.html#${group.id}">查看 Skill ${icon('arrow-up-right')}</a><span role="status" id="copy-status"></span></div>`;
  let template=false;
  const paint=()=>{
    const values=[...document.querySelectorAll('[data-prompt-index]')].map(input=>input.value.trim());
    $('#prompt-text').textContent=template?templates[group.id]:templates[group.id].replace(/【([^】]+)】/g,(match,key)=>values[tags.indexOf(key)]||match);
    $('.prompt-fields').hidden=template;
    for(const btn of document.querySelectorAll('[data-prompt-mode]')) btn.setAttribute('aria-pressed',String((btn.dataset.promptMode==='template')===template));
    $('#copy-status').textContent='';
  };
  for(const btn of document.querySelectorAll('[data-prompt-mode]'))btn.onclick=()=>{template=btn.dataset.promptMode==='template';paint();};
  $('#prompt-content').oninput=paint;
  $('#copy-prompt').onclick=async()=>{
    try {await navigator.clipboard.writeText($('#prompt-text').textContent);$('#copy-status').textContent='已复制';}
    catch {
      const range=document.createRange();
      range.selectNodeContents($('#prompt-text'));
      getSelection().removeAllRanges();getSelection().addRange(range);
      $('#copy-status').textContent=document.execCommand('copy')?'已复制':'已选中，请手动复制';
    }
  };
  paint();
  promptDialog.showModal();
}

document.addEventListener('click',event=>{
  const ctl=event.target.closest('button,a');
  for(const panel of document.querySelectorAll('.tools[open]')){
    if(!panel.contains(event.target)||ctl?.hasAttribute('data-prompt')){
      if(panel.contains(event.target))$('summary',panel).focus({preventScroll:true});
      panel.open=false;
    }
  }
  if(!ctl)return;
  if(ctl.dataset.close)$('#'+ctl.dataset.close).close();
  if(ctl.dataset.prompt)openPrompt(ctl.dataset.prompt);
  if(ctl.dataset.series){sheet.close();changeSeries(ctl.dataset.series);}
  if(ctl.dataset.post)openViewer(screenPosts.find(post=>post.id===ctl.dataset.post),ctl);
});
for(const modal of [sheet,promptDialog]) modal.addEventListener('click',event=>{if(event.target===modal)modal.close();});
$('#home').onclick=event=>{event.preventDefault();changeSeries('all');};
$('#search-toggle').onclick=()=>discloseSearch($('#search-row').hidden);
box.oninput=()=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>{window.scrollTo(0,0);resetGrid();},140);};
box.onkeydown=event=>{if(event.key==='Escape')discloseSearch(false);};
category.onchange=()=>{subgroup=category.value;window.scrollTo(0,0);resetGrid();};
$('#series-search').oninput=renderSeriesList;
$('#series-toggle').onclick=()=>{$('#series-search').value='';renderSeriesList();sheet.showModal();};
$('#swipe-toggle').onclick=event=>openViewer(screenPosts[0],event.currentTarget);
$('#viewer-like').onclick=()=>{if(activeRendered)localLike(activeRendered.id);};
$('#photo-prev').onclick=()=>changePhoto(photoIndex-1);
$('#photo-next').onclick=()=>changePhoto(photoIndex+1);
more.onclick=()=>more.textContent==='重试加载'?resetGrid():append();
const initial=new URL(location).searchParams.get('series');
if(series.has(initial)||initial==='liked') {filter=initial;resetGrid();}
else {
  observeThumbnails(gallery);
  more.hidden=seedCount>=conf.count;
  observeMore();
}
