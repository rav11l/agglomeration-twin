/* Parse the actual inline scripts, including the complete embedded module. */
const fs=require('node:fs');
const vm=require('node:vm');
for(const file of ['site/republic_embed.html','site/agglomeration-twin_page.html']){
  let count=0;
  for(const m of fs.readFileSync(file,'utf8').matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)){
    if(/type\s*=\s*["']application\/json["']/.test(m[1]))continue;
    new vm.Script(m[2],{filename:file+':script'+(++count)});
  }
  if(!count)throw new Error('No scripts found: '+file);
  console.log(file+': '+count+' inline scripts compile');
}
