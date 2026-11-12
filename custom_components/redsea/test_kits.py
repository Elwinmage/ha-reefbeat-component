"""Titration test kits: from the reagent volume to the test result.

A titration kit is read on its syringe: either the volume of reagent used
to reach the colour change (Red Sea, Colombo), or the volume left in a 1 mL
syringe filled before the test (Salifert). The result is proportional to
the reagent used, so a kit is a factor (unit of the parameter per mL used)
and the way its syringe is read.

Factors come from the kits' instructions (see ``source``). Pure module: no
Home Assistant import, used by dose_regulation.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

# The test result is typed in by hand
MANUAL: Final[str] = "manual"


@dataclass(frozen=True, slots=True)
class TitrationKit:
    """A titration test kit.

    ``reading`` is "used" (the syringe tells the reagent used; it can be
    refilled, so more than ``capacity`` may be used) or "remaining" (the
    syringe, filled to ``capacity`` before the test, tells what is left).
    """

    brand: str
    parameter: str
    factor: float
    reading: str
    capacity: float = 1.0
    source: str = ""

    def value(self, reagent_ml: float) -> float:
        """Test result for a syringe reading.

        @raise ValueError: a reading the syringe cannot give
        """
        if reagent_ml < 0:
            raise ValueError("the reagent volume cannot be negative")
        if self.reading == "remaining":
            if reagent_ml > self.capacity:
                raise ValueError(
                    f"at most {self.capacity} mL can be left in the syringe"
                )
            used = self.capacity - reagent_ml
        else:
            used = reagent_ml
        return used * self.factor


# Ids are stable: they are stored in the settings of the heads
TEST_KITS: Final[dict[str, TitrationKit]] = {
    # 10 mL sample, 0.01 mL = 0.14 dKH (0.05 meq/L); syringe refilled above
    # 14 dKH
    "redsea_kh": TitrationKit(
        "Red Sea", "kh", 14.0, "used", source="Red Sea KH/Alkalinity Pro manual"
    ),
    # 5 mL sample, 0.01 mL = 5 ppm
    "redsea_ca": TitrationKit(
        "Red Sea", "ca", 500.0, "used", source="Red Sea Calcium Pro manual"
    ),
    # 2 mL sample, 0.01 mL = 20 ppm
    "redsea_mg": TitrationKit(
        "Red Sea", "mg", 2000.0, "used", source="Red Sea Magnesium Pro manual"
    ),
    # 4 mL sample: dKH = (1 - reading) x 16
    "salifert_kh": TitrationKit(
        "Salifert", "kh", 16.0, "remaining", source="Salifert KH/Alk table"
    ),
    # 3 mL sample: ppm = (1 - reading) x 500
    "salifert_ca": TitrationKit(
        "Salifert", "ca", 500.0, "remaining", source="Salifert Ca table"
    ),
    # 2 mL sample: ppm = (1 - reading) x 1500
    "salifert_mg": TitrationKit(
        "Salifert", "mg", 1500.0, "remaining", source="Salifert Mg table"
    ),
    # 5 mL sample: KH = mL of KH-2 used x 20
    "colombo_kh": TitrationKit(
        "Colombo", "kh", 20.0, "used", source="Colombo Marine KH test manual"
    ),
}


def kits_for(parameter: str) -> list[str]:
    """Options of the kit select for a parameter: manual entry first."""
    return [MANUAL, *(k for k, kit in TEST_KITS.items() if kit.parameter == parameter)]


def kit_value(kit_id: str, reagent_ml: float) -> float | None:
    """Test result of a kit for a reading, None for manual entry.

    @raise ValueError: unknown kit or impossible reading
    """
    if kit_id == MANUAL:
        return None
    kit = TEST_KITS.get(kit_id)
    if kit is None:
        raise ValueError(f"unknown test kit {kit_id!r}")
    return kit.value(reagent_ml)
