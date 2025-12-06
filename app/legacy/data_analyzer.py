# data_analyzer.py
import pandas as pd
import numpy as np
from scipy.optimize import curve_fit
from app_logic import SPHERE_DATA

# --- Core Data Analysis Functions ---

def fit_curve(x_data, y_data, func_type='linear'):
    """
    Performs curve fitting on x and y data.
    :param func_type: 'linear', 'poly2' (polynomial degree 2), or 'custom'
    """
    x = np.array(x_data)
    y = np.array(y_data)
    
    if func_type == 'linear':
        def linear_func(x, a, b):
            return a * x + b
        try:
            popt, pcov = curve_fit(linear_func, x, y)
            return f"Linear Fit: y = {popt[0]:.3f}x + {popt[1]:.3f}", linear_func(x, *popt)
        except RuntimeError:
            return "Error: Could not perform linear fit.", None

    elif func_type == 'poly2':
        # Polynomial of degree 2: a*x^2 + b*x + c
        popt = np.polyfit(x, y, 2)
        poly_func = np.poly1d(popt)
        return f"Quadratic Fit: y = {popt[0]:.3f}x^2 + {popt[1]:.3f}x + {popt[2]:.3f}", poly_func(x)

    else:
        return "Unsupported fit type.", None

def propagate_error(formula_str, values_dict, errors_dict):
    """
    Stub for error propagation.
    In a full implementation, this would use partial derivatives (symbolic math) 
    or Monte Carlo methods. Here, we provide a placeholder.
    """
    if 'm' in values_dict and 'a' in values_dict and formula_str.lower() == 'f = ma':
        # Simple example: F = ma, error in F is sqrt((a*dm)^2 + (m*da)^2)
        m = values_dict['m']
        a = values_dict['a']
        dm = errors_dict.get('m', 0.1) # Default error
        da = errors_dict.get('a', 0.1)
        
        dF = np.sqrt((a * dm)**2 + (m * da)**2)
        F = m * a
        return f"Result: F = {F:.2f} $\pm$ {dF:.2f} N"
    
    return "Error propagation result placeholder."

def get_dataset_summary():
    """Provides a brief summary of the merged SPHERE dataset."""
    if not SPHERE_DATA.empty:
        summary = {
            "Total Records": len(SPHERE_DATA),
            "Columns": len(SPHERE_DATA.columns),
            "Example Columns": list(SPHERE_DATA.columns[:5]),
            "Missing Values Check": SPHERE_DATA.isnull().sum().sum()
        }
        return summary
    return {"Status": "Dataset not loaded."}
