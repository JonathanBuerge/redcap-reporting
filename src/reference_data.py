import numpy as np

# ---------------------------------------------------------
# 1. Sprunghöhe (Jump Height)
# Quelle: Sumnik et al. (2013)
# Methode: LMS (Lambda, Mu, Sigma) mit fixem L=0.5
# ---------------------------------------------------------
JUMP_HEIGHT_LMS = {
    'girls': {
        6:  (0.5, 0.27, 0.18), 7:  (0.5, 0.28, 0.18), 8:  (0.5, 0.29, 0.17),
        9:  (0.5, 0.31, 0.17), 10: (0.5, 0.32, 0.16), 11: (0.5, 0.33, 0.16),
        12: (0.5, 0.34, 0.16), 13: (0.5, 0.35, 0.15), 14: (0.5, 0.36, 0.15),
        15: (0.5, 0.37, 0.15), 16: (0.5, 0.38, 0.15), 17: (0.5, 0.38, 0.14),
        18: (0.5, 0.38, 0.14)
    },
    'boys': {
        6:  (0.5, 0.25, 0.20), 7:  (0.5, 0.27, 0.19), 8:  (0.5, 0.29, 0.18),
        9:  (0.5, 0.32, 0.18), 10: (0.5, 0.34, 0.17), 11: (0.5, 0.36, 0.16),
        12: (0.5, 0.39, 0.16), 13: (0.5, 0.41, 0.15), 14: (0.5, 0.44, 0.15),
        15: (0.5, 0.46, 0.14), 16: (0.5, 0.48, 0.14), 17: (0.5, 0.50, 0.13),
        18: (0.5, 0.52, 0.13)
    }
}

# ---------------------------------------------------------
# 2. VO2max (VO2peak) in mL/kg/min
# Quelle: Bongers et al. (2014) - DOI: 10.13140/2.1.3422.6884
# Methode: Polynom-Regression für den Mittelwert (P50)
# Standardabweichung (SD) ca. 4.5 mL/kg/min (geschätzt aus Daten) für Perzentile
# ---------------------------------------------------------

def get_vo2max_reference(age, sex):
    """
    Berechnet P3, P10, P25, P50, P75, P90, P97 für ein gegebenes Alter.
    sex: 'girls' (1) oder 'boys' (2)
    """
    # Formeln aus Bongers et al. 2014
    if sex == 'girls':
        # Female equation: (-0.0025 * age^3) + (0.064 * age^2) - (0.1483 * age) + 37.968
        mean = (-0.0025 * (age**3)) + (0.064 * (age**2)) - (0.1483 * age) + 37.968
        sd = 4.2 # Ca. Wert für Mädchen in dieser Altersgruppe
    else:
        # Male equation: (-0.0015 * age^3) - (0.0321 * age^2) + (1.8851 * age) + 33.355
        mean = (-0.0015 * (age**3)) - (0.0321 * (age**2)) + (1.8851 * age) + 33.355
        sd = 4.8 # Ca. Wert für Jungs

    # Z-Scores für Perzentile
    z_scores = {
        'P3': -1.88, 'P10': -1.28, 'P25': -0.675,
        'P50': 0,
        'P75': 0.675, 'P90': 1.28, 'P97': 1.88
    }

    result = {}
    for p, z in z_scores.items():
        result[p] = mean + (z * sd)
    
    return result