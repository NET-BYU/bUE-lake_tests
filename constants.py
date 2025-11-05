"""Simple Dictionary to map Reyex names to bUE names"""

bUEs = {"10": "Doof", "70": "Vanessa", "30": "Major", "40": "Buford", "50": "Carl", "60": "Monty", "20": "Monty"}

bUEs_inverted = {
    "Doof": "10",
    "Vanessa": "70",
    "Major": "30",
    "Buford": "40",
    "Carl": "50",
    "Perry": "60",
}

""" Defines how many seconds pass until the base station/bUE consider themselves disconnected 
    TIMEOUT * 10 seconds must pass"""
TIMEOUT = 6
