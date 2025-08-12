"""Simple Dictionary to map Reyex names to bUE names"""

bUEs = {
    "10": "Doof",
    "80": "Candace",
    "30": "Major",
    "40": "Buford",
    "50": "Carl",
    "60": "Perry",
}

bUEs_inverted = {
    "Doof": "10",
    "Candace": "80",
    "Major": "30",
    "Buford": "40",
    "Carl": "50",
    "Perry": "60",
}

""" Defines how many seconds pass until the base station/bUE consider themselves disconnected 
    TIMEOUT * 10 seconds must pass"""
TIMEOUT = 6
