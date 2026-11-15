"""Read the RocketPy_27 Excel workbook without changing its layout.

The RocketPy workbook uses vertical ``Name``/``Value`` tables and has trailing
spaces in two sheet names.  This adapter intentionally matches sheet names
after stripping whitespace and returns the parameter dictionary already used
by SPLATsim's input panel.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openpyxl import load_workbook


def _sheet(wb, requested: str):
    """Return a sheet using an exact or whitespace-insensitive name match."""
    if requested in wb.sheetnames:
        return wb[requested]
    matches = {name.strip(): name for name in wb.sheetnames}
    try:
        return wb[matches[requested.strip()]]
    except KeyError as exc:
        raise ValueError(
            f"Sheet {requested!r} not found. Available sheets: {wb.sheetnames}"
        ) from exc


def _table(ws) -> dict[str, Any]:
    """Read a RocketPy vertical A/B table, ignoring section headers."""
    values: dict[str, Any] = {}
    for name, value in ws.iter_rows(min_row=2, max_col=2, values_only=True):
        if not isinstance(name, str) or value is None:
            continue
        key = name.strip()
        if not key:
            continue
        if isinstance(value, str):
            stripped = value.strip()
            try:
                value = float(stripped)
                if value.is_integer():
                    value = int(value)
            except ValueError:
                if stripped.lower() in {"true", "false"}:
                    value = stripped.lower() == "true"
                else:
                    value = stripped
        values[key] = value
    return values


def _number(values: dict[str, Any], key: str) -> float | None:
    value = values.get(key)
    return (
        float(value)
        if isinstance(value, (int, float)) and not isinstance(value, bool)
        else None
    )


@dataclass(frozen=True)
class RocketPyWorkbook:
    """Workbook values used by SPLATsim, plus source metadata."""

    path: Path
    parameters: dict[str, Any]
    structure: dict[str, Any]
    propellant: dict[str, Any]
    simulation: dict[str, Any]
    splatsim: dict[str, Any]

    @property
    def splat_parameters(self) -> dict[str, dict[str, Any]]:
        structure = self.structure
        simulation = self.simulation
        splatsim = self.splatsim

        def value(key: str, fallback: Any) -> Any:
            return splatsim.get(key, fallback)

        # The generated Simulation sheet is preferred for masses and apogee.
        # Fall back to the workbook inputs when the simulation has not run yet.
        mass = _number(simulation, "Wet mass (initial) [kg]")
        if mass is None:
            mass = _number(structure, "m_dry_measured")

        apogee = _number(simulation, "Apogee AGL [m]")
        if apogee is None:
            apogee = 3000.0

        trigger_altitude = _number(structure, "trig_alt_para") or 400.0
        open_cd = _number(structure, "drag_coeff_para_unreefed") or 1.5
        reefed_cd = _number(structure, "drag_coeff_para_reefed")

        # RocketPy specifies recovery deployment by altitude.  SPLATsim starts
        # at the event altitude, so use the RocketPy trigger altitude as the
        # first event and do not add an extra time-based free-fall interval.
        return {
            "rocket": {
                "mass": value("rocket_mass", mass or 83.0),
                "diameter": value(
                    "rocket_diameter", 2 * (_number(structure, "r_rocket") or 0.1215)
                ),
                "drag_coefficient": value(
                    "rocket_drag_coeff", _number(structure, "drag_coeff_rocket") or 0.75
                ),
            },
            "parachute": {
                "projected_diameter": value("parachute_diameter", 5.0),
                "open_Cd": value("open_cd", open_cd),
                "reefed_Cd": value("reefed_cd", reefed_cd),
                "reefing_ratio": value("reefing_ratio", 0.25),
                "spill_hole_diameter": value("spill_hole_diameter", 0.0),
                "opening_time": value("opening_time", 0.0),
            },
            "environment": {
                "air_density": value("air_density", 1.124),
                "gravity": value("gravity", 9.81),
            },
            "simulation": {
                "type": value("sim_type", "Dual Event"),
                "first_altitude": value("first_altitude", apogee),
                "second_altitude": value("second_altitude", trigger_altitude),
                "launch_angle": value("launch_angle", 90.0),
                "time_step": value("time_step", 0.01),
                "max_time": value("max_time", 1200.0),
                "reefed": value("reefed", True),
            },
            "rocketpy": {
                "source": str(self.path),
                "apogee_agl": apogee,
                "apogee_asl": _number(simulation, "Apogee ASL [m]"),
                "time_to_apogee": _number(simulation, "Time to apogee [s]"),
                "max_speed": _number(simulation, "Max velocity [m/s]"),
                "max_acceleration": _number(simulation, "Max acceleration [m/s^2]"),
                "max_mach": _number(simulation, "Max Mach [-]"),
                "rail_exit_velocity": _number(simulation, "Rail exit velocity [m/s]"),
                "static_margin_liftoff": _number(
                    simulation, "Static margin liftoff [c]"
                ),
                "static_margin_rail_exit": _number(
                    simulation, "Static margin rail exit [c]"
                ),
            },
        }


def load_rocketpy_parameters(filepath: str | Path) -> RocketPyWorkbook:
    """Load a RocketPy_27-compatible workbook for use in SPLATsim."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Excel file not found: {path}")
    wb = load_workbook(path, data_only=True, read_only=True)
    return RocketPyWorkbook(
        path=path,
        parameters=_table(_sheet(wb, "Parameters")),
        structure=_table(_sheet(wb, "Structure")),
        propellant=_table(_sheet(wb, "Propellant")),
        simulation=_table(_sheet(wb, "Simulation")),
        splatsim=(
            _table(_sheet(wb, "SPLATsim"))
            if any(s.strip().lower() == "splatsim" for s in wb.sheetnames)
            else {}
        ),
    )
