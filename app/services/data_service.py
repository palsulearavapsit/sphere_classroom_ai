# Lazy imports for scientific libraries
try:
    import numpy as np
    from scipy.optimize import curve_fit
    DATA_ANALYSIS_AVAILABLE = True
except ImportError:
    np = None
    curve_fit = None
    DATA_ANALYSIS_AVAILABLE = False
    print("Data analysis libraries not available - data service will work in basic mode")


def _poly(x, *coeffs):
    return sum(c*(x**i) for i,c in enumerate(coeffs))

def fit_curve(payload:dict):
    # payload: { x:[], y:[], kind:"linear"|"poly", degree:int }
    if not DATA_ANALYSIS_AVAILABLE:
        return {"error": "Data analysis libraries not available", "model": "unavailable"}
        
    x = np.array(payload.get("x",[]), dtype=float)
    y = np.array(payload.get("y",[]), dtype=float)
    kind = payload.get("kind","linear")
    if kind == "linear":
        A = np.vstack([x, np.ones_like(x)]).T
        m, c = np.linalg.lstsq(A, y, rcond=None)[0]
        yhat = m*x + c
        return {"model":"linear","params":{"m":m,"c":c},"yhat":yhat.tolist()}
    if kind == "poly":
        degree = int(payload.get("degree",2))
        p, _ = curve_fit(lambda xx,*pp:_poly(xx,*pp), x, y, p0=[0]*(degree+1))
        yhat = _poly(x, *p)
        return {"model":"poly","params":{"coeffs":list(map(float,p))},"yhat":yhat.tolist()}
    return {"error":"unknown kind"}

def propagate_error(payload:dict):
    # payload: { formula:"m*a", values:{m:1.0,a:2.0}, errors:{m:0.1,a:0.2} }
    # basic linearized propagation
    if not DATA_ANALYSIS_AVAILABLE:
        return {"error": "Data analysis libraries not available", "value": 0, "sigma": 0}
        
    import sympy as sp
    formula = payload.get("formula","")
    values = payload.get("values",{})
    errors = payload.get("errors",{})
    syms = {k: sp.symbols(k) for k in values.keys()}
    f = sp.sympify(formula)
    variance = 0
    for k,v in values.items():
        df = sp.diff(f, syms[k])
        variance += float((df.subs({syms[t]:values[t] for t in values})**2)) * (errors.get(k,0)**2)
    val = float(f.subs({syms[t]:values[t] for t in values}))
    return {"value": val, "sigma": float(np.sqrt(variance))}

def analyze_experiment(payload:dict):
    # simple descriptive stats
    if not DATA_ANALYSIS_AVAILABLE:
        return {"error": "Data analysis libraries not available", "mean": 0, "std": 0, "min": 0, "max": 0, "n": 0}
        
    arr = np.array(payload.get("data",[]), dtype=float)
    if arr.size == 0:
        return {"error":"no data"}
    return {
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr, ddof=1)) if arr.size>1 else 0.0,
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "n": int(arr.size),
        "hist": np.histogram(arr, bins=min(10, arr.size))[0].tolist()
    }
