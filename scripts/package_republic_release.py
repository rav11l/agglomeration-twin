"""Create the source/data/offline-HTML release archive from an explicit manifest."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def package():
    manifest=json.loads((ROOT/'release_manifest.json').read_text(encoding='utf-8'))
    generated=['site/tatarstan_twin_2026-11-26.html',
               'site/tatarstan_overview_2026-11-26.png',
               'outputs/republic/enrichment.json',
               'outputs/republic/vacancies_registry_2026-11-26.csv']
    files=sorted(set(manifest['files']+generated))
    output=ROOT/'outputs/republic/publication'
    output.mkdir(parents=True,exist_ok=True)
    prefix='agglomeration-twin-v'+manifest['version']
    target=output/(prefix+'.zip')
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name in files:
            file=ROOT/name
            if not file.is_file():
                raise FileNotFoundError(f'Build the release first: {name}')
            archive.write(file,prefix+'/'+name)
    digest=hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix('.zip.sha256').write_text(digest+'  '+target.name+'\n',encoding='ascii')
    print(json.dumps({'archive':str(target),'files':len(files),'bytes':target.stat().st_size,'sha256':digest}))


if __name__=='__main__':
    package()
