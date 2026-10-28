"""Премия за близость к метро: МНК по log цены м² (ЕИСЖС, сентябрь 2026), ошибки кластеризованы по ЖК."""
import pathlib, pandas as pd, statsmodels.formula.api as smf
ROOT = pathlib.Path(__file__).resolve().parents[1]
d = pd.read_csv(ROOT/'data/hedonic_sample.csv')
d['cls2'] = d.cls.replace({'Типовой': 'Комфорт'})   # 4 типовых дома объединены с комфортом
print(len(d), 'buildings,', d.zk.nunique(), 'complexes')
for f in ['lp~m1+ldc+C(cls2)', 'lp~m15+ldc+C(cls2)', 'lp~ldm+ldc+C(cls2)', 'lp~m1+ldc+C(cls2)+sold']:
    m = smf.ols(f, d).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.zk)[0]})
    k = [x for x in m.params.index if x in ('m1', 'm15', 'ldm')][0]
    lo, hi = m.conf_int().loc[k]
    print(f"{f:29} {k}={m.params[k]:.3f} se {m.bse[k]:.3f} CI [{lo:.3f}, {hi:.3f}] ldc {m.params['ldc']:.3f} R2 {m.rsquared:.3f}" + (f" premium {100*(2.718281828**m.params[k]-1):.1f}%" if k != 'ldm' else '') + f" n {int(m.nobs)}")
