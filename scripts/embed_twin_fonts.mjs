/** Cache the same open web fonts as the published twin, including Cyrillic. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
export async function embedFonts(){
 const chars=[...Array.from({length:95},(_,i)=>String.fromCharCode(32+i)),
  ...Array.from({length:64},(_,i)=>String.fromCharCode(0x410+i)),'Ё','ё','₽','№','×','—','–','«','»','©','·','…','−','≤','≥','₂','τ','Σ'].join('');
 const url='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&display=swap&text='+encodeURIComponent(chars);
 const r=await fetch(url,{signal:AbortSignal.timeout(15000)});
 if(!r.ok)throw Error('Google Fonts CSS '+r.status);let css=await r.text();
 const urls=[...new Set([...css.matchAll(/url\((https:[^)]+)\)/g)].map(m=>m[1]))];
 if(!urls.length)throw Error('No font URLs in the published-font request.');
 const dir=path.join(root,'site/assets/fonts');await fs.mkdir(dir,{recursive:true});
 const records=[];
 for(let i=0;i<urls.length;i++){
  const res=await fetch(urls[i],{signal:AbortSignal.timeout(15000)});
  if(!res.ok)throw Error('Font HTTP '+res.status);const buf=Buffer.from(await res.arrayBuffer());
  const magic=buf.subarray(0,4).toString('hex');
  const ext=magic==='00010000'?'ttf':magic==='4f54544f'?'otf':'woff2';
  const type=ext==='ttf'?'font/ttf':ext==='otf'?'font/otf':'font/woff2';
  const name='twin_'+i+'.'+ext;await fs.writeFile(path.join(dir,name),buf);
  css=css.replaceAll(urls[i],'data:'+type+';base64,'+buf.toString('base64'));
  records.push({url:urls[i],file:'site/assets/fonts/'+name,bytes:buf.length,sha256:createHash('sha256').update(buf).digest('hex')});
 }
 let licenses='';
 for(const family of ['inter','sourceserif4']){
  const licenseURL='https://raw.githubusercontent.com/google/fonts/main/ofl/'+family+'/OFL.txt';
  const res=await fetch(licenseURL,{signal:AbortSignal.timeout(15000)});
  if(!res.ok)throw Error('Font license '+res.status);let text=await res.text();
  await fs.writeFile(path.join(dir,family+'_OFL.txt'),text);licenses+='\n/* '+text.replaceAll('*/','* /')+' */\n';
 }
 await fs.writeFile(path.join(root,'site/republic_fonts.css'),css+licenses);
 await fs.writeFile(path.join(dir,'metadata.json'),JSON.stringify({css_url:url,fonts:records},null,2));
 return{families:['Inter','Source Serif 4'],files:records.length,bytes:records.reduce((s,x)=>s+x.bytes,0),offline:true};
}
