"""
calculator.py – Kleinwasserzuschlag (Low Water Surcharge) Calculator
=====================================================================
Calculates the KWZ surcharge applied to Rhine barge freight based on the
water level at the Kaub gauge.  These surcharges are triggered when low
water restricts vessel draught, reducing cargo capacity per barge and
increasing per-ton shipping costs.
"""


def calculate_surcharge(water_level_cm: float, cargo_tonnage: float) -> dict:
    """Calculate the Kleinwasserzuschlag for a given water level and cargo.

    Parameters
    ----------
    water_level_cm : float
        Current (or forecasted) water level at Kaub in centimetres.
    cargo_tonnage : float
        Total cargo weight in metric tonnes.

    Returns
    -------
    dict  {"surcharge_per_ton": float, "total_surcharge": float}
    """
    if water_level_cm > 150:
        surcharge_per_ton = 0.0
    elif 131 <= water_level_cm <= 150:
        surcharge_per_ton = 15.0
    elif 111 <= water_level_cm <= 130:
        surcharge_per_ton = 30.0
    elif 91 <= water_level_cm <= 110:
        surcharge_per_ton = 45.0
    elif 80 <= water_level_cm <= 90:
        surcharge_per_ton = 65.0
    else:  # water_level_cm < 80
        surcharge_per_ton = 90.0

    return {
        "surcharge_per_ton": surcharge_per_ton,
        "total_surcharge": surcharge_per_ton * cargo_tonnage,
    }


def compare_freight_costs(cargo_tonnage: float, total_barge_surcharge: float) -> dict:
    """Compare total freight costs across Barge, Truck, and Rail.

    Parameters
    ----------
    cargo_tonnage : float
        Cargo weight in metric tonnes.
    total_barge_surcharge : float
        Total Kleinwasserzuschlag already calculated for this cargo.

    Returns
    -------
    dict  {"Barge": float, "Truck": float, "Rail": float}
    """
    barge_base_rate = 20.0   # €/ton
    truck_base_rate = 55.0   # €/ton
    rail_base_rate  = 45.0   # €/ton

    return {
        "Barge": (cargo_tonnage * barge_base_rate) + total_barge_surcharge,
        "Truck": cargo_tonnage * truck_base_rate,
        "Rail":  cargo_tonnage * rail_base_rate,
    }


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 55)
    print("  Kleinwasserzuschlag (Low Water Surcharge) Calculator")
    print("=" * 55)

    # Test 1 – Normal conditions (186 cm) → no surcharge
    result_normal = calculate_surcharge(water_level_cm=186, cargo_tonnage=1000)
    print("\n📦 Test 1 – Normal conditions (186 cm, 1 000 t)")
    print(f"   Surcharge/ton : €{result_normal['surcharge_per_ton']:.2f}")
    print(f"   Total cost    : €{result_normal['total_surcharge']:,.2f}")

    costs_normal = compare_freight_costs(1000, result_normal["total_surcharge"])
    print(f"   Barge: €{costs_normal['Barge']:,.2f}  |  "
          f"Truck: €{costs_normal['Truck']:,.2f}  |  "
          f"Rail: €{costs_normal['Rail']:,.2f}")

    # Test 2 – Severe drought (85 cm) → €65/ton
    result_drought = calculate_surcharge(water_level_cm=85, cargo_tonnage=1000)
    print("\n🏜  Test 2 – Severe drought (85 cm, 1 000 t)")
    print(f"   Surcharge/ton : €{result_drought['surcharge_per_ton']:.2f}")
    print(f"   Total cost    : €{result_drought['total_surcharge']:,.2f}")

    costs_drought = compare_freight_costs(1000, result_drought["total_surcharge"])
    print(f"   Barge: €{costs_drought['Barge']:,.2f}  |  "
          f"Truck: €{costs_drought['Truck']:,.2f}  |  "
          f"Rail: €{costs_drought['Rail']:,.2f}")

    print("\n" + "=" * 55)
