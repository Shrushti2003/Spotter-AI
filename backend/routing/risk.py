from enum import IntEnum
class Risk(IntEnum):
    LOW = 0; MODERATE = 1; HIGH = 2; SEVERE = 3; NO_TRAVEL = 4
def wind_risk(mph):
    if mph < 25: return Risk.LOW
    if mph < 35: return Risk.MODERATE
    if mph < 45: return Risk.HIGH
    if mph < 55: return Risk.SEVERE
    return Risk.NO_TRAVEL
def rain_risk(v):
    if v < .10: return Risk.LOW
    if v <= .25: return Risk.MODERATE
    if v <= .50: return Risk.HIGH
    if v <= 1.00: return Risk.SEVERE
    return Risk.NO_TRAVEL
def snow_risk(v):
    if v < .5: return Risk.LOW
    if v <= 1.0: return Risk.MODERATE
    if v <= 2.0: return Risk.HIGH
    if v <= 3.0: return Risk.SEVERE
    return Risk.NO_TRAVEL
def checkpoint_risk(wind_mph, rain_inph, snow_inph, load_lb):
    components = {"wind": wind_risk(wind_mph), "rain": rain_risk(rain_inph), "snow": snow_risk(snow_inph)}
    risk = max(components.values())
    if wind_mph >= 55 or (45 <= wind_mph < 55 and load_lb > 30000): risk = Risk.NO_TRAVEL
    elif 35 <= wind_mph < 45 and load_lb > 40000: risk = max(risk, Risk.SEVERE)
    return risk, components
def risk_name(risk): return risk.name.lower()

