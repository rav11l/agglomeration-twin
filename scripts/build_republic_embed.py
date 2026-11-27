"""Build a Tilda HTML block, isolated from the existing twin by Shadow DOM.

Usage: python scripts/build_republic_embed.py --data-ref <immutable Git commit>
The standalone HTML remains an offline alternative. Existing sections are kept.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START = '<!-- republic-v0.3.2:start -->'
END = '<!-- republic-v0.3.2:end -->'


def build(data_ref):
    if not re.fullmatch(r'[0-9a-f]{40}', data_ref):
        raise ValueError('Use an immutable 40-character Git commit SHA.')
    template = (ROOT / 'site/republic_template.html').read_text(encoding='utf-8')
    markup = template.split('<main id="app">', 1)[1].split('</main>', 1)[0]
    markup = markup[markup.index('<div class="stats"'):]
    markup = markup.split('<footer class="footer">', 1)[0]
    markup = markup.replace('HTML работает без подключения к сети.',
                            'Данные этого блока загружаются из зафиксированной версии Git; автономный HTML доступен в выпуске.')
    css = (ROOT / 'site/republic.css').read_text(encoding='utf-8')
    css = css.replace(':root{', ':host{').replace('}body{', '}:host{')
    css += '\n' + (ROOT / 'site/republic_embed_theme.css').read_text(encoding='utf-8').strip()
    css += '#app{padding:0;max-width:none}.module-heading{padding:0 0 18px}.module-heading p{font-size:14px;color:var(--muted);margin-top:9px}'
    css = css.replace('linear-gradient(90deg,#E7EEF6,#1D4E8C)',
                      'linear-gradient(90deg,#E6E9EE,#142233)')
    css = css.replace('background:#5F86AE', 'background:#6B86A3')
    code = template.split('<script>\n', 1)[1].split('</script>', 1)[0]
    code = code.replace("const D=JSON.parse(document.getElementById('twin-data').textContent),N=D.profiles.length;",
                        'const N=D.profiles.length;')
    code = code.replace('__TWIN_I18N__', (ROOT / 'site/republic_i18n.js').read_text(encoding='utf-8'))
    code = code.replace('document.getElementById(', 'root.getElementById(')
    code = code.replace('document.querySelectorAll(', 'root.querySelectorAll(')
    code = code.replace('b=[29,78,140]', 'b=[20,34,51]')
    code = code.replace('a=[231,238,246]', 'a=[230,233,238]')
    heading = '<div class="module-heading"><h2>Работа, вакансии и жильё во всех 45 МО</h2><p>43 района, Казань и Набережные Челны · версия 0.3.2 · данные собраны 26 ноября 2026 года</p></div>'
    html = '<style>' + css + '</style><div id="app">' + heading + markup + '</div>'
    compressed = ROOT / 'outputs/republic/enrichment.json.gz'
    digest = hashlib.sha256(compressed.read_bytes()).hexdigest()
    url = f'https://raw.githubusercontent.com/rav11l/agglomeration-twin/{data_ref}/outputs/republic/enrichment.json.gz'
    module = START + '''
<section id="tw-republic-2026" style="max-width:1080px;margin:28px auto;padding:0 16px;box-sizing:border-box">
  <p role="status">Загрузка карты всех 45 муниципалитетов…</p>
</section>
<script>
(() => {
  'use strict';
  const host=document.getElementById('tw-republic-2026');
  if(!host||host.shadowRoot)return;
  const isEn=()=>document.querySelector('#dgl-tw')?.dataset.lang==='en';
  const text=(ru,en)=>isEn()?en:ru;
  const target=document.getElementById('tw-s-lvl');
  if(target){target.before(host);host.style.padding='0';}
  const nav=document.getElementById('tw-nav');
  if(nav&&!nav.querySelector('a[href="#tw-republic-2026"]')){
    const link=document.createElement('a');link.href='#tw-republic-2026';link.dataset.t='tw-republic-2026';
    link.innerHTML='<span data-ru>Работа и вакансии · 45 МО</span><span data-en>Jobs and vacancies · 45 municipalities</span>';
    const group=nav.querySelector('a[data-t="tw-eco"]')?.parentElement||nav;
    group.appendChild(link);
  }
  const root=host.attachShadow({mode:'open'});
  host.replaceChildren();
  root.innerHTML='<p role="status" style="font:14px/1.6 Jost,sans-serif;color:#5F6873">'+text('Загрузка карты всех 45 муниципалитетов…','Loading the map of all 45 municipalities…')+'</p>';
  async function load(){
    try{
      if(!window.DecompressionStream)throw new Error('browser');
      const total=__BYTES__,step=131072;
      let loaded=0;
      const chunks=await Promise.all(Array.from({length:Math.ceil(total/step)},async(_,index)=>{
        const from=index*step,to=Math.min(total-1,from+step-1);
        const response=await fetch(DATA_URL,{headers:{Range:'bytes='+from+'-'+to},signal:AbortSignal.timeout(25000)});
        if(response.status!==206)throw new Error('HTTP '+response.status);
        const bytes=new Uint8Array(await response.arrayBuffer());
        if(bytes.length!==to-from+1)throw new Error('range length');
        loaded+=bytes.length;
        const status=root.querySelector('[role="status"]');
        if(status)status.textContent=text('Загрузка данных карты · ','Loading map data · ')+Math.round(loaded/total*100)+'%';
        return bytes;
      }));
      const combined=new Uint8Array(total);
      chunks.forEach((bytes,index)=>combined.set(bytes,index*step));
      const buffer=combined.buffer;
      const actual=[...new Uint8Array(await crypto.subtle.digest('SHA-256',buffer))].map(x=>x.toString(16).padStart(2,'0')).join('');
      if(actual!==DATA_SHA256)throw new Error('checksum');
      const stream=new Blob([buffer]).stream().pipeThrough(new DecompressionStream('gzip'));
      const D=await new Response(stream).json();
      if(D.version!=='0.3.2'||D.profiles.length!==45||!D.checks.vacancy_region_complete)throw new Error('schema');
      root.innerHTML=MODULE_HTML;
      (function(root,D){
MODULE_CODE
      })(root,D);
    }catch(error){
      console.error('Republic twin could not load:',error);
      root.innerHTML='<div style="font:14px/1.6 Jost,sans-serif;padding:18px;border:1px solid #E2DED6;background:#FBFAF7"><p>Не удалось загрузить данные карты. Проверьте подключение или откройте автономный HTML из <a href="https://github.com/rav11l/agglomeration-twin" target="_blank" rel="noopener">репозитория и выпуска Zenodo</a>.</p><button type="button">Повторить загрузку</button></div>';
      if(isEn()){root.querySelector('p').innerHTML='Map data could not be loaded. Check your connection or open the offline HTML from the <a href="https://github.com/rav11l/agglomeration-twin" target="_blank" rel="noopener">repository or Zenodo release</a>.';root.querySelector('button').textContent='Retry loading';}
      root.querySelector('button').addEventListener('click',load);
    }
  }
  const DATA_URL=__URL__,DATA_SHA256=__HASH__,MODULE_HTML=__HTML__;
  load();
})();
</script>
''' + END
    module = module.replace('MODULE_CODE', code).replace('__URL__', json.dumps(url))
    module = module.replace('__BYTES__', str(compressed.stat().st_size))
    module = module.replace('__HASH__', json.dumps(digest)).replace('__HTML__', json.dumps(html, ensure_ascii=False))
    (ROOT / 'site/republic_embed.html').write_text(module, encoding='utf-8')
    page_path = ROOT / 'site/agglomeration-twin_page.html'
    page = page_path.read_text(encoding='utf-8')
    page = re.sub(r'<!-- republic-v[0-9.]+:start -->.*?<!-- republic-v[0-9.]+:end -->', '', page, flags=re.S)
    anchor = '<section id="tw-s-lvl"'
    if page.count(anchor) != 1:
        raise ValueError('The existing page insertion point changed; review before replacing.')
    page = page.replace(anchor, module + '\n' + anchor)
    page = page.replace('Версия 0.1.3 · 04.11.2026', 'Версия 0.3.2 · 26.11.2026')
    page = page.replace('Version 0.1.3 · 4 Nov 2026', 'Version 0.3.2 · 26 Nov 2026')
    page_path.write_text(page, encoding='utf-8')
    print(json.dumps({'embed_bytes':len(module.encode('utf-8')), 'data_ref':data_ref, 'sha256':digest}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-ref',required=True)
    build(parser.parse_args().data_ref)

