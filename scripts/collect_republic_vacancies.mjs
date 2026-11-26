/** Regional public API collection with page audit and no personal contacts. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
export const base='https://opendata.trudvsem.ru/api/v1/vacancies/region/1600000000000';
const limit=100;
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function number(v){if(v===null||v===undefined||v==='')return null;const x=Number(v);return Number.isFinite(x)?x:null}
export function project(v){
 let name=v.company?.name||'';
 if(/^(ИП\s|Индивидуальный предприниматель)/i.test(name))name='Индивидуальный предприниматель';
 return {id:String(v.id),source:'trudvsem',url:v.vac_url||'',title:v['job-name']||'',
  employer:name,employer_code:v.company?.companycode||'',
  salary_min:number(v.salary_min),salary_max:number(v.salary_max),currency:v.currency||'',
  work_places:number(v.work_places),schedule:v.schedule||'',employment:v.employment||'',
  education:v.requirement?.education||'',specialisation:v.category?.specialisation||'',
  creation_date:v['creation-date']||null,modification_date:v.date_modify||null,
  portal_region_code:v.region?.region_code||null,
  addresses:(v.addresses?.address||[]).map(a=>({location:a.location||'',lat:number(a.lat),lon:number(a.lng)}))};
}
export async function fetchPage(offset,{attempts=3,timeout=25000}={}){
 const url=base+'?offset='+offset+'&limit='+limit;
 let last;
 for(let attempt=0;attempt<attempts;attempt++){
  try{
   const response=await fetch(url,{signal:AbortSignal.timeout(timeout),headers:{'User-Agent':'DigitalEconomyLab-AgglomerationTwin/0.3 (+https://digitaleconomylab.ru/agglomeration-twin)'}});
   const text=await response.text();
   if(!response.ok)throw Error('HTTP '+response.status);
   const data=JSON.parse(text);
   if(String(data.status)!=='200'||!Array.isArray(data.results?.vacancies))throw Error('Invalid API response');
   const records=data.results.vacancies.map(x=>project(x.vacancy));
   return {records,audit:{page:offset,url,returned:records.length,reported_total:Number(data.meta.total),
    retrieved_at:new Date().toISOString(),http_date:response.headers.get('date'),
    raw_sha256:createHash('sha256').update(text).digest('hex')}};
  }catch(e){last=e;if(attempt+1<attempts)await pause(700*(attempt+1));}
 }
 throw last;
}
export async function collect({workers=4}={}){
 const dir=path.join(root,'data/republic/vacancy_pages_2026-11-26');await fs.mkdir(dir,{recursive:true});
 for(const page of [0,1]){const f=path.join(dir,String(page).padStart(3,'0')+'.json');try{await fs.access(f)}catch{await fs.writeFile(f,JSON.stringify(await fetchPage(page)))}}
 const zero=JSON.parse(await fs.readFile(path.join(dir,'000.json'),'utf8'));
 const baseCount=Math.min(100,Math.ceil(zero.audit.reported_total/100));
 while(true){const saved=(await fs.readdir(dir)).filter(n=>/^\d{3}\.json$/.test(n)&&Number(n.slice(0,3))<baseCount).length;if(saved>=baseCount)break;
  const r=await collectBatch({workers,maxPages:Math.min(16,baseCount-saved)});
  if(r.pages<=saved)throw Error('Collection made no progress: '+JSON.stringify(r.batch_failures));
 }
 const specs=await getRepairSpecs(),ties=specs.filter(x=>x.label!=='tail'),windows=[];let cursor=0;
 async function worker(){while(cursor<ties.length){const w=ties[cursor++];windows.push(await fetchWindow(w.from,w.to,w.label))}}
 await Promise.all(Array.from({length:Math.min(workers,3)},worker));
 const tail=specs.find(x=>x.label==='tail');windows.push(await fetchWindow(tail.from,tail.to,tail.label));
 const result=await assembleComplete(windows);
 if(!result.complete)throw Error('Coverage mismatch: '+JSON.stringify(result));
 return result;
}

/** Resume in bounded batches so an interrupted REPL cannot discard progress. */
export async function collectBatch({maxPages=16,workers=4}={}){
 const dir=path.join(root,'data/republic/vacancy_pages_2026-11-26');
 await fs.mkdir(dir,{recursive:true});
 const zero=JSON.parse(await fs.readFile(path.join(dir,'000.json'),'utf8'));
 const total=zero.audit.reported_total,count=Math.ceil(total/limit);
 const existing=new Set((await fs.readdir(dir)).filter(n=>/^\d{3}\.json$/.test(n)).map(n=>Number(n.slice(0,3))));
 const pending=Array.from({length:count},(_,i)=>i).filter(i=>!existing.has(i)).slice(0,maxPages);
 let next=0;const failed=[];
 async function worker(){while(next<pending.length){const page=pending[next++];try{
  const r=await fetchPage(page,{attempts:2,timeout:18000});
  await fs.writeFile(path.join(dir,String(page).padStart(3,'0')+'.json'),JSON.stringify(r));
 }catch(e){failed.push({page,error:String(e)})}}}
 await Promise.all(Array.from({length:workers},worker));
 const pages=[];
 for(let i=0;i<count;i++){try{pages.push(JSON.parse(await fs.readFile(path.join(dir,String(i).padStart(3,'0')+'.json'),'utf8')))}catch{}}
 const records=pages.flatMap(p=>p.records),unique=new Map(records.map(r=>[r.employer_code+'|'+r.id,r]));
 const totals=[...new Set(pages.map(p=>p.audit.reported_total))],missing=Array.from({length:count},(_,i)=>i).filter(i=>!pages.some(p=>p.audit.page===i));
 const complete=!missing.length&&records.length===total&&unique.size===total&&totals.length===1;
 const summary={total,fetched:records.length,unique:unique.size,pages:pages.length,
  expected_pages:count,complete,missing_pages:missing,batch_failures:failed};
 await fs.writeFile(path.join(root,'data/republic/vacancies_collection_progress.json'),JSON.stringify(summary,null,2));
 if(complete){const result={collection_timestamp:new Date().toISOString(),
  collection_started:zero.audit.retrieved_at,scope:'regional_snapshot',source_urls:[base],
  region_total:total,fetched_records:records.length,unique_records:unique.size,
  duplicate_records:records.length-unique.size,pages_requested:count,pages_received:pages.length,
  failed_pages:[],reported_totals:totals,pagination:'page_index',complete:true,
  page_audit:pages.map(p=>p.audit),records:[...unique.values()],
  notes:['Full regional query; no title-search sampling.','Completeness is relative to this portal, not the whole labour market.','Contact fields, resumes and full descriptions are not exported.']};
  await fs.writeFile(path.join(root,'data/republic/vacancies_2026-11-26.json'),JSON.stringify(result));
 }
 return summary;
}

export async function fetchWindow(from,to,label){
 // This API accepts second-precision UTC timestamps, but returns HTTP 500
 // for otherwise valid ISO strings containing milliseconds or +0300.
 from=from?from.replace(/\.\d{3}Z$/,'Z'):null;
 to=to.replace(/\.\d{3}Z$/,'Z');
 const dir=path.join(root,'data/republic/vacancy_supplements_2026-11-26');
 await fs.mkdir(dir,{recursive:true});
 const records=[],audit=[];
 let expected=null;
 for(let page=0;page<(expected===null?1:Math.ceil(expected/100));page++){
  const params=new URLSearchParams({offset:String(page),limit:'100',modifiedTo:to});
  if(from)params.set('modifiedFrom',from);
  const url=base+'?'+params;
  let obtained;
  for(let attempt=0;attempt<3;attempt++){
   try{const r=await fetch(url,{signal:AbortSignal.timeout(20000)});const text=await r.text();
    if(!r.ok)throw Error('HTTP '+r.status);const data=JSON.parse(text);
    if(String(data.status)!=='200')throw Error('API '+data.status);
    const n=Number(data.meta.total);
    if(n>=10401)throw Error('Date filter was not applied; refusing an unbounded supplement.');
    if(expected===null)expected=n;else if(expected!==n)throw Error('Window count changed');
    obtained={records:(data.results?.vacancies||[]).map(x=>project(x.vacancy)),
     audit:{window:label,page,url,returned:data.results?.vacancies?.length||0,reported_total:n,
      retrieved_at:new Date().toISOString(),raw_sha256:createHash('sha256').update(text).digest('hex')}};
    break;
   }catch(e){if(attempt===2)throw e;await pause(800)}
  }
  records.push(...obtained.records);audit.push(obtained.audit);
  await fs.writeFile(path.join(dir,label+'_'+String(page).padStart(3,'0')+'.json'),JSON.stringify(obtained));
 }
 return {window:label,expected,returned:records.length,unique:new Set(records.map(x=>x.employer_code+'|'+x.id)).size,pages:audit.length};
}

export async function getRepairSpecs(){
 const dir=path.join(root,'data/republic/vacancy_pages_2026-11-26'),pages=[];
 for(const n of (await fs.readdir(dir)).filter(n=>/^\d{3}\.json$/.test(n)).sort())pages.push(JSON.parse(await fs.readFile(path.join(dir,n),'utf8')));
 const groups=new Map();for(const p of pages)for(const r of p.records){let k=r.employer_code+'|'+r.id;if(!groups.has(k))groups.set(k,[]);groups.get(k).push(r)}
 const dates=[...new Set([...groups.values()].filter(v=>v.length>1).map(v=>v[0].modification_date))];
 const specs=dates.map((t,i)=>{let ms=new Date(t).getTime();return {label:'tie_'+i,from:new Date(ms-1000).toISOString(),to:new Date(ms+1000).toISOString()}});
 const oldest=Math.min(...pages.flatMap(p=>p.records.map(r=>new Date(r.modification_date).getTime())));
 specs.push({label:'tail',from:null,to:new Date(oldest+1000).toISOString()});return specs;
}

export async function assembleComplete(windows=[]){
 const files=[];
 for(const folder of ['vacancy_pages_2026-11-26','vacancy_supplements_2026-11-26']){
  const dir=path.join(root,'data/republic',folder);
  for(const name of (await fs.readdir(dir)).filter(n=>n.endsWith('.json')).sort())files.push(JSON.parse(await fs.readFile(path.join(dir,name),'utf8')));
 }
 const total=files[0].audit.reported_total,records=files.flatMap(p=>p.records),unique=new Map(records.map(r=>[r.employer_code+'|'+r.id,r]));
 const complete=unique.size===total;
 const result={collection_timestamp:new Date().toISOString(),collection_started:files[0].audit.retrieved_at,
  scope:'regional_snapshot',source_urls:[base],region_total:total,fetched_records:records.length,
  unique_records:unique.size,duplicate_records:records.length-unique.size,
  pages_requested:files.length,pages_received:files.length,failed_pages:[],complete,
  retrieval_strategy:'base_pages_and_modified_date_windows',page_audit:files.map(f=>f.audit),
  supplement_windows:windows,records:[...unique.values()],
  notes:['Regional API rows deduplicated by employer and vacancy ID.',
   'Equal update timestamps can overlap adjacent pages; narrow modified-date windows repair boundary omissions.',
   'The tail is retrieved with a date filter to avoid the API deep-pagination error.',
   'Complete means all records declared by this portal, not the whole labour market.',
   'Contact fields, resumes and full descriptions are not exported.']};
 const dest=path.join(root,'data/republic',complete?'vacancies_2026-11-26.json':'vacancies_incomplete_2026-11-26.json');
 await fs.writeFile(dest,JSON.stringify(result));
 return {file:dest,total,unique:unique.size,fetched:records.length,complete,queries:files.length,windows};
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{console.log(JSON.stringify(await collect(),null,2))}catch(e){console.error(String(e));process.exitCode=1}
}
