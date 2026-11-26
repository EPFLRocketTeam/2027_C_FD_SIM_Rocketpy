"""Run the independent SPLATsim parachute model from a RocketPy workbook."""

from __future__ import annotations

from pathlib import Path
import sys

import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPLATSIM_ROOT = PROJECT_ROOT / "SPLATsim"
if str(SPLATSIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SPLATSIM_ROOT))

from integration import load_rocketpy_parameters
from models import HemisphericalParachute, RocketModel
from simulation import DualEventSimulation, SingleEventSimulation


def run_splatsim_parachute(workbook_path: str | Path):
    """Run SPLATsim using the ``SPLATsim`` sheet in ``workbook_path``."""
    workbook = load_rocketpy_parameters(workbook_path)
    params = workbook.splat_parameters
    rocket_values = params["rocket"]
    parachute_values = params["parachute"]
    environment_values = params["environment"]
    simulation_values = params["simulation"]

    parachute = HemisphericalParachute(
        projected_diameter=parachute_values["projected_diameter"],
        open_Cd=parachute_values["open_Cd"],
        reefing_ratio=parachute_values["reefing_ratio"],
        spill_hole_diameter=parachute_values["spill_hole_diameter"],
        opening_time=parachute_values["opening_time"],
        reefed_Cd_override=parachute_values.get("reefed_Cd"),
    )
    rocket = RocketModel(
        mass=rocket_values["mass"],
        diameter=rocket_values["diameter"],
        parachute=parachute,
        drag_coefficient=rocket_values["drag_coefficient"],
    )

    common = dict(
        rocket=rocket,
        parachute=parachute,
        reefed=simulation_values["reefed"],
        time_step=simulation_values["time_step"],
        max_time=simulation_values["max_time"],
        launch_angle=simulation_values["launch_angle"],
        air_density=environment_values["air_density"],
        gravity=environment_values["gravity"],
    )
    if simulation_values["type"] == "Dual Event":
        simulation = DualEventSimulation(
            first_event_altitude=simulation_values["first_altitude"],
            second_event_altitude=simulation_values["second_altitude"],
            **common,
        )
    else:
        simulation = SingleEventSimulation(
            first_event_altitude=simulation_values["first_altitude"],
            **common,
        )

    results = simulation.simulate()
    _show_results(results, workbook.path)
    return results


def _show_results(results, workbook_path):
    """Display independent SPLATsim parachute plots and key values."""
    figure, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    time = results["time"]

    axes[0].plot(time, results["altitude"], color="tab:red")
    axes[0].set_ylabel("Altitude (m)")
    axes[0].set_title("SPLATsim parachute calculation")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(time, results["velocity"], color="tab:green")
    axes[1].set_ylabel("Velocity (m/s)")
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(
        time,
        [value / 9.81 for value in results["acceleration"]],
        color="tab:blue",
    )
    axes[2].set_ylabel("Acceleration (g)")
    axes[2].set_xlabel("Time (s)")
    axes[2].grid(True, alpha=0.3)

    figure.suptitle(f"SPLATsim recovery model — {Path(workbook_path).name}")
    figure.tight_layout()
    figure._splatsim_results = results
    figure.show()

    print("\n========== SPLATSIM PARACHUTE SUMMARY ==========")
    print(f"Workbook: {workbook_path}")
    print(f"Landing velocity: {results['landing_velocity']:.3f} [m/s]")
    print(f"Flight time: {results['flight_time']:.3f} [s]")
    print(f"Maximum altitude: {max(results['altitude']):.3f} [m]")
    print(f"Maximum velocity: {max(results['velocity']):.3f} [m/s]")
    print(f"Maximum acceleration: {max(results['acceleration']):.3f} [m/s^2]")
    print("===============================================\n")
