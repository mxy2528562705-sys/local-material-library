'use strict';
const $ = id => document.getElementById(id);
let token = '', offset = 0, total = 0, selected = null, page = 1, hitOffset = 0;
let listSequence = 0, readerSequence = 0, wasRunning = false;
const statuses = {native:'已提取', pending:'待 OCR', ocr:'已 OCR', failed:'OCR 失败'};
const imageTypes = new Set(['.pdf','.jpg','.jpeg','.png','.webp','.tif','.tiff','.bmp']);
function node(tag, text, className) { const n = document.createElement(tag); n.textContent = text; if(className) n.className=className; return n; }
function highlight(text, q) {
  const fragment = document.createDocumentFragment();
  if(!q) { fragment.append(document.createTextNode(text)); return fragment; }
  let start=0, at; const lower=text.toLowerCase(), key=q.toLowerCase();
  while((at=lower.indexOf(key,start)) !== -1) {fragment.append(document.createTextNode(text.slice(start,at)),node('mark',text.slice(at,at+q.length)));start=at+q.length;}
  fragment.append(document.createTextNode(text.slice(start))); return fragment;
}
async function api(path, body) {
  const response=await fetch(path, body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json','X-Library-Token':token},body:JSON.stringify(body)});
  const result=await response.json(); if(!response.ok) throw Error(result.error || '请求失败'); return result;
}
function showError(error) {$('error').hidden=false;$('error').textContent=error.message;}
async function load() {
  const sequence=++listSequence;
  try {
    const q=$('search').value.trim();
    const data=await api('/api/files?'+new URLSearchParams({q,category:$('category').value,state:$('state').value,offset}));
    if(sequence !== listSequence) return;
    total=data.total; $('count').textContent=`${total} 份资料`;
    const category=$('category').value; $('category').replaceChildren(new Option('全部分类',''),...data.categories.map(c=>new Option(c,c)));$('category').value=category;
    $('results').replaceChildren();
    for(const item of data.items) {
      const row=node('article','', 'item');
      let thumb=node('span',item.ext.slice(1).toUpperCase(),'thumb file-icon');
      if(imageTypes.has(item.ext) && !item.missing && !item.error) {thumb=document.createElement('img');thumb.className='thumb';thumb.loading='lazy';thumb.alt='';thumb.src=`/api/page/${item.id}/1`;thumb.onerror=()=>thumb.replaceWith(node('span',item.ext.slice(1).toUpperCase(),'thumb file-icon'));}
      const text=node('div','');const title=node('p','','name');title.append(highlight(item.name,q));text.append(title,node('p',item.path,'path'));
      if(item.snippet) {const snippet=node('p','','snippet');snippet.append(highlight(item.snippet,q));text.append(snippet);}
      const classification=node('div','','classification');classification.append(node('span',item.category,'badge'));if(item.tags)classification.append(node('p',item.tags,'meta'));
      const processing=node('div','','processing'); processing.append(node('p',`${(item.size/1048576).toFixed(1)} MB · ${item.ext==='.pdf'?item.pages+' 页':item.ext.slice(1).toUpperCase()}`,'meta'));
      for(const [status,count] of Object.entries(item.counts))processing.append(node('span',`${statuses[status]} ${count}`,`badge ${status==='pending'?'warning':status==='failed'?'danger':''}`));
      if(item.missing || item.error)processing.append(node('span',item.missing?'原文件缺失':item.error,'badge danger'));
      const open=node('button','查看','open');open.onclick=()=>openReader(item.id,item.hit);
      row.append(thumb,text,classification,processing,open);$('results').append(row);
    }
    if(!data.items.length)$('results').append(node('p','没有匹配的资料','empty'));
    $('prev').disabled=offset===0;$('next').disabled=offset+30>=total;$('range').textContent=total?`${offset+1}–${Math.min(offset+30,total)} / ${total}`:'0 / 0';
  } catch(error) {showError(error);}
}
async function openReader(id, number=1) {
  hitOffset=0;selected=id;page=number;$('saved').textContent='';
  if(!$('reader').open)$('reader').showModal();
  await readPage(true);
}
async function readPage(reset=false) {
  const sequence=++readerSequence;
  try {
    const data=await api(`/api/file/${selected}?`+new URLSearchParams({page,q:$('search').value.trim(),offset:hitOffset}));
    if(sequence!==readerSequence)return;
    $('filename').textContent=data.name;$('filepath').textContent=data.path;
    $('page-number').value=page;$('page-number').max=Math.max(1,data.pages);$('page-total').textContent=data.ext==='.pdf'?`/ ${data.pages} 页`:'/ 1';
    $('page-prev').disabled=page<=1;$('page-next').disabled=page>=data.pages;
    $('original').href=`/api/original/${selected}`;
    $('preview-error').hidden=true;
    const visual=imageTypes.has(data.ext);$('page-image').hidden=!visual;$('page-text').hidden=visual;$('transcript').hidden=!visual;
    if(visual) {
      $('page-image').hidden=true;
      $('page-image').onload=()=>{if(sequence===readerSequence)$('page-image').hidden=false;};
      $('page-image').onerror=()=>{if(sequence===readerSequence){$('preview-error').hidden=false;$('preview-error').textContent='当前页加载失败，请检查原文件并重试。';}};
      $('page-image').src=`/api/page/${selected}/${page}`;
    }
    for(const id of ['page-text','extracted'])$(''+id).replaceChildren(highlight(data.page.text,$('search').value.trim()));
    $('page-status').textContent=(statuses[data.page.status]||data.page.status)+(data.page.error?`：${data.page.error}`:'');
    if(data.ext==='.docx')$('page-status').textContent+=' · DOCX 文字视图';
    if(reset) {$('edit-category').value=data.category;$('edit-tags').value=data.tags;$('edit-notes').value=data.notes;}
    $('hide').textContent=data.hidden?'恢复到资料列表':'隐藏此条目';$('hide').onclick=async()=>{try{await api(`/api/edit/${selected}`,{hidden:!data.hidden});$('reader').close();await load();}catch(error){showError(error);}};
    $('hits').replaceChildren();
    for(const hit of data.hits) {const b=node('button',`第 ${hit} 页`);b.onclick=()=>{page=hit;readPage();};$('hits').append(b);}
    if(hitOffset>0){const b=node('button','上一组命中');b.onclick=()=>{hitOffset-=50;readPage();};$('hits').append(b);}
    if(hitOffset+50<data.hit_total){const b=node('button','下一组命中');b.onclick=()=>{hitOffset+=50;readPage();};$('hits').append(b);}
    $('page-view').scrollIntoView({block:'nearest'});
  } catch(error) {$('preview-error').hidden=false;$('preview-error').textContent=error.message;}
}
$('close').onclick=()=>{$('reader').close();++readerSequence;};
$('page-prev').onclick=()=>{page--;readPage();};$('page-next').onclick=()=>{page++;readPage();};
$('page-number').onchange=()=>{const n=Number($('page-number').value);if(Number.isInteger(n)&&n>=1&&n<=Number($('page-number').max)){page=n;readPage();}else $('page-number').value=page;};
$('metadata').onsubmit=async event=>{event.preventDefault();try{await api(`/api/edit/${selected}`,{category:$('edit-category').value,tags:$('edit-tags').value,notes:$('edit-notes').value});$('saved').textContent='已保存';await load();}catch(error){$('saved').textContent=error.message;}};
let debounce; $('search').oninput=()=>{clearTimeout(debounce);debounce=setTimeout(()=>{offset=0;load();},200);};
for(const id of ['category','state'])$(id).onchange=()=>{offset=0;load();};
$('prev').onclick=()=>{offset=Math.max(0,offset-30);load();};$('next').onclick=()=>{offset+=30;load();};
for(const id of ['scan','ocr'])$(id).onclick=async()=>{try{$('error').hidden=true;await api('/api/'+id,{});await status();}catch(error){showError(error);}};
async function status() {try{const data=await api('/api/status');token=data.token;document.title=data.title;$('title').textContent=data.title;$('job').textContent=data.job.message;for(const id of ['scan','ocr'])$(id).disabled=data.job.running;if(data.job.error)showError(Error(data.job.error));if(wasRunning&&!data.job.running)await load();wasRunning=data.job.running;}catch(error){showError(error);}}
async function init(){await status();await load();setInterval(status,2000);}init();
