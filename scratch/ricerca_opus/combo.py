exec(open("fund.py").read().split("# target")[0])
a = store.load("armor_index").dropna(); F["armor"] = a.resample("ME").last().reindex(M.index)
print("armor da", a.index[0].date())
def ddh(h):
    return pd.Series([ (sp[(sp.index>t)&(sp.index<=t+pd.DateOffset(months=h))].min()/M[t]-1)*100 if t < sp.index[-1]-pd.DateOffset(months=h) else np.nan for t in M.index], M.index)
for h in [3, 6, 12]:
    y = (ddh(h) <= -10).astype(float).where(ddh(h).notna())
    for cols in [["armor"], ["armor", "eps_g12"], ["armor", "eps_g12", "cape", "curve_min12"], ["eps_g12", "cape", "curve_min12", "baa_d6", "claims_d6", "sma10"]]:
        X = F[cols]; ok = X.notna().all(1) & y.notna(); Xo, yo = X[ok], y[ok]
        P, Y, C = [], [], []
        for yr in range(2003, 2027):
            te = Xo.index.year == yr
            tr = Xo.index < pd.Timestamp(f"{yr}-01-01") - pd.DateOffset(months=h)
            if not te.any() or tr.sum() < 60 or yo[tr].nunique() < 2: continue
            sc = StandardScaler().fit(Xo[tr]); md = LogisticRegression(C=0.3, max_iter=500).fit(sc.transform(Xo[tr]), yo[tr])
            P += list(md.predict_proba(sc.transform(Xo[te]))[:, 1]); Y += list(yo[te]); C += [yo[tr].mean()] * te.sum()
        P, Y, C = map(np.array, (P, Y, C))
        print(h, cols, len(Y), "AUC", round(roc_auc_score(Y, P), 3), "BSS", round(1 - np.mean((P-Y)**2)/np.mean((C-Y)**2), 3))
