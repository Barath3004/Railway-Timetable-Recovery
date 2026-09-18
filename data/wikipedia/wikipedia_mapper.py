"""
Wikipedia Mapper

Converts raw Wikipedia parser output
into our project's standard schema.

Responsibilities
----------------
1. Interpret raw Wikipedia fields.
2. Convert them into project-standard fields.
3. Clean and standardize values.
4. Never modify HTML or perform parsing.
"""

import re


class WikipediaMapper:

    def __init__(self, wiki_data):
        self.raw = wiki_data
        self.cleaned = {}

    # -------------------------------------------------------
    # Generic Field Lookup
    # -------------------------------------------------------

    def get_value(self, *keys):
        """
        Return the first non-empty value found
        from the supplied Wikipedia field names.
        """

        for key in keys:

            value = self.raw.get(key)

            if value:
                return value.strip()

        return ""

    # -------------------------------------------------------
    # Helper Functions
    # -------------------------------------------------------

    def normalize_station_code(self, code):
        """
        Remove Wikipedia references and
        standardize station code.
        """

        code = re.sub(r"\[.*?\]", "", code)
        code = code.strip().upper()

        return code

    def normalize_station_name(self, name):
        """
        Clean station names and remove
        duplicate / alias values.
        """

        name = re.sub(r"\[.*?\]", "", name).strip()

        # Remove duplicated full name
        words = name.split()

        half = len(words) // 2

        if (
            len(words) % 2 == 0
            and words[:half] == words[half:]
        ):
            words = words[:half]

        name = " ".join(words)

        # Common aliases found on Wikipedia
        replacements = {
            "Chennai Egmore Chennai Elumbur": "Chennai Egmore",
            "Chennai Egmore Chennai Ezhumbur": "Chennai Egmore",
            "Arakkonam Junction Arakkonam Junction": "Arakkonam Junction",
            "Tambaram Thaambaram": "Tambaram",
            "Chengalpattu Junction Chingalput Junction": "Chengalpattu Junction",
        }

        return replacements.get(name, name)

    def normalize_zone(self, zone):
        """
        Standardize railway zone names.
        """

        zone = zone.replace(" zone", "")
        zone = zone.replace(" Zone", "")
        zone = zone.strip()

        mapping = {
            "Southern Railways": "Southern Railway",
            "South Western Railways": "South Western Railway",
            "South Central Railways": "South Central Railway",
            "Indian Railways": ""
        }

        return mapping.get(zone, zone)

    # -------------------------------------------------------
    # Station Code
    # -------------------------------------------------------

    def map_station_code(self):

        code = self.get_value(
            "Station code",
            "Code"
        )

        self.cleaned["station_code"] = self.normalize_station_code(code)

    # -------------------------------------------------------
    # Station Name
    # -------------------------------------------------------

    def map_station_name(self):

        name = self.get_value(
            "Station Name"
        )

        self.cleaned["station_name"] = self.normalize_station_name(name)

    # -------------------------------------------------------
    # Railway Zone
    # -------------------------------------------------------

    def map_zone(self):

        zone = self.get_value(
            "Zone(s)",
            "Zone",
            "Fare zone"
        )

        self.cleaned["railway_zone"] = self.normalize_zone(zone)

    # -------------------------------------------------------
    # Railway Division
    # -------------------------------------------------------

    def map_division(self):

        division = self.get_value(
            "Division(s)",
            "Division"
        )

        self.cleaned["railway_division"] = division

    # -------------------------------------------------------
    # Platform Details
    # -------------------------------------------------------

    def map_platforms(self):

        text = self.get_value(
            "Platforms",
            "Platform"
        )

        total = 0
        mainline = 0
        suburban = 0

        numbers = [int(n) for n in re.findall(r"\d+", text)]

        if numbers:
            total = numbers[0]

        match = re.search(
            r"(\d+)\s*main.*?(\d+)\s*.*suburban",
            text,
            re.IGNORECASE
        )

        if match:

            mainline = int(match.group(1))
            suburban = int(match.group(2))

        else:

            mainline = total
            suburban = 0

        self.cleaned["platforms_total"] = total
        self.cleaned["mainline_platforms"] = mainline
        self.cleaned["suburban_platforms"] = suburban

    # -------------------------------------------------------
    # Electrification Year
    # -------------------------------------------------------

    def map_electrified(self):

        text = self.get_value(
            "Electrified",
            "Electrification"
        )

        year = re.search(
            r"(18|19|20)\d{2}",
            text
        )

        if year:
            self.cleaned["electrified"] = int(year.group())
        else:
            self.cleaned["electrified"] = 0

    # -------------------------------------------------------
    # Execute Complete Mapping
    # -------------------------------------------------------

    def map_all(self):

        self.map_station_code()
        self.map_station_name()
        self.map_zone()
        self.map_division()
        self.map_platforms()
        self.map_electrified()

        return self.cleaned