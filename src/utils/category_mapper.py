def map_category(raw: str) -> str:
    raw = raw.lower().strip()

    mapping = {
        "colombia": "Nacional",
        "zona caribe": "Regional",
        "atlantico": "Regional",
        "soledad": "Regional",
        "barranquilla": "Regional",
        "liga colombiana": "Deportes",
        "liga-colombiana": "Deportes",
        "luto": "Social",
        "cartagena": "Regional",
        "tour de francia": "Deportes",
        "generales": "General",
        "mundo": "Internacional",
        "podcast": "Podcast",
        "política": "Política",
        "politica": "Política",
        "sociales": "Social",
        "eventos": "Social",
        "deportes": "Deportes",
        "tecnología": "Tecnología",
        "tecnologia": "Tecnología",
        "multimedia": "Multimedia"
    }

    return mapping.get(raw, "General")
