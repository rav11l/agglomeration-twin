"""Exact-data overview for the republic preview, not an HTML screenshot."""
import json
from pathlib import Path
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import Polygon
from matplotlib.cm import ScalarMappable
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
D = json.loads((ROOT / 'outputs/republic/enrichment.json').read_text(encoding='utf-8'))
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11})
for font in (ROOT / 'site/assets/fonts').glob('twin_*'):
    font_manager.fontManager.addfont(str(font))
plt.rcParams['font.family'] = 'Inter' if (ROOT / 'site/assets/fonts').exists() else 'DejaVu Sans'
ink, muted, teal = '#15181C', '#5F6873', '#1D3C5C'
fig = plt.figure(figsize=(14, 8.3), facecolor='#FBFAF7')
fig.text(.04,.946,'DIGITAL ECONOMY LAB',color=teal,size=11,weight=600)
fig.text(.04,.877,'Двойник агломераций Татарстана',color=ink,size=30,fontfamily='Source Serif 4')
fig.text(.04,.833,'43 района, Казань и Набережные Челны · все 45 муниципалитетов',color=muted,size=13)
fig.text(.96,.946,'26.11.2026 · версия 0.3.1',ha='right',color=muted,size=11)
ax=fig.add_axes([.025,.22,.62,.56]);ax.set_aspect('equal');ax.axis('off')
geo={r['id']:r for r in D['geometry']};vals=[p['workers_per100'] for p in D['profiles']]
norm=Normalize(min(vals),max(vals));cmap=LinearSegmentedColormap.from_list('dgl',['#E7EEF6','#1D4E8C'])
points=[]
for i,p in enumerate(D['profiles']):
 r=geo[p['slug']]
 for part in r['path'].split('M')[1:]:
  pts=[(float(a),float(b)) for a,b in re.findall(r'(-?[\d.]+),(-?[\d.]+)',part)]
  if len(pts)>2:
   ax.add_patch(Polygon(pts,closed=True,facecolor=cmap(norm(vals[i])),edgecolor='white',linewidth=.8))
   points+=pts
for p in D['profiles']:
 if p['is_core']:
  r=geo[p['slug']]
  ax.scatter([r['cx']],[r['cy']],s=21,c=teal,edgecolors='white',zorder=5)
  label=p['short'];dx,dy=(-9,-7) if p['slug']=='казань' else (0,-8)
  ax.annotate(label,(r['cx'],r['cy']),xytext=(dx,dy),textcoords='offset points',ha='center',
              size=10,color=ink,weight=600,bbox={'facecolor':'#ffffffdd','edgecolor':'none','pad':2},zorder=6)
ax.set_xlim(min(x for x,y in points)-5,max(x for x,y in points)+5)
ax.set_ylim(max(y for x,y in points)+7,min(y for x,y in points)-7)
cax=fig.add_axes([.09,.175,.48,.014]);cb=fig.colorbar(ScalarMappable(norm=norm,cmap=cmap),cax=cax,orientation='horizontal')
cb.outline.set_visible(False);cb.ax.tick_params(labelsize=9,length=0)
cb.set_label('Работников организаций без МСП на 100 жителей · 2024',fontsize=10,color=muted)
C=D['checks'];left=.69
fig.text(left,.735,f"{C['population_total']:,}".replace(',',' '),size=29,weight=600,color=ink)
fig.text(left,.699,'жителей · Росстат, 01.01.2024',size=11,color=muted)
fig.text(left,.625,f"{C['employees_total']:,}".replace(',',' '),size=29,weight=600,color=teal)
fig.text(left,.589,'работников организаций без МСП · 2024',size=10,color=muted)
fig.text(left,.513,f"{C['housing_assigned_flats']:,}".replace(',',' '),size=29,weight=600,color=ink)
fig.text(left,.477,f"квартир в {C['housing_assigned_buildings']} объектах ЕИСЖС · 27.10.2026",size=10,color=muted)
fig.text(left,.397,'В интерактивном HTML',size=14,weight=600,color=teal)
for k,s in enumerate([('7' if C['vacancy_region_complete'] else '6')+' слоёв карты и 45 профилей','Фильтры трёх агломераций','Поиск и сортировка районов','Сценарии новых рабочих мест']):
 fig.text(left,.359-k*.037,s,size=11,color=ink)
if C['vacancy_region_complete']:
    vacancy_note=(f"Работа России: {C['vacancy_unique_collected']:,} объявление; "
                  f"{C['vacancy_audit']['assigned']:,} привязаны к МО, {C['vacancy_unassigned']} адресов требуют проверки.").replace(',', ' ')
else:
    vacancy_note='Вакансии: неполная подборка; отсутствие данных не заменено нулём.'
fig.text(.04,.09,vacancy_note,size=10,color=muted)
fig.text(.04,.038,'Источники: Росстат, ЕИСЖС, OSRM · геометрия © участники OpenStreetMap, ODbL. Карта построена из данных HTML-превью.',size=9,color=muted)
target=ROOT/'site/tatarstan_overview_2026-11-26.png';fig.savefig(target,dpi=150,facecolor=fig.get_facecolor());print(target)
