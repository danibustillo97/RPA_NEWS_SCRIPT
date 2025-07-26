from src.sources_config.sources import LEAGUE_KEYWORDS, COUNTRIES, TEAMS


def classify_league(text: str):
    text = text.lower()
    for keyword, league in LEAGUE_KEYWORDS.items():
        if keyword in text:
            return league
    return None

def classify_country(text: str):
    text = text.lower()
    for country in COUNTRIES:
        if country in text:
            return country.capitalize()
    return None

def classify_team(text: str):
    text = text.lower()
    for team in TEAMS:
        if team in text:
            return team.capitalize()
    return None
