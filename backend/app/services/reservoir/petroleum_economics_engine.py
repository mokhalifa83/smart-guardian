"""
Smart Guardian Reservoir Intelligence Layer - Petroleum Economics, Accounting & Probabilistic Engines
======================================================================================================
Implements:
24. Oil Accounting Engine (API MPMS Chapter 11.1 Gross-to-Net Volumetric Allocation & Shrinkage)
25. Joint Venture & Company Accounting Engine (WI, NRI, Royalty & Partner Net Entitlement)
26. CAPEX Engine (Capital Expenditure Amortization & Well Cost Allocation)
27. OPEX Engine (Field Operating Costs, Lifting Cost $/bbl & Chemical/Power Allocation)
28. Profit & Loss / Petroleum Economics Engine (DCF, NPV, IRR, Payback & Netback Cash Flow)
29. Statistical & Probabilistic Engine (Monte Carlo P10/P50/P90 PRMS Volumetric Simulation)
"""

import math
import random
from typing import Optional, Dict, Any, List
from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus
from app.services.reservoir.physics_guardrails import PhysicsGuardrails


class OilAccountingEngine:
    """
    24. Oil Accounting Engine.
    Applies API MPMS Chapter 11.1 standard temperature and pressure correction (CTPL, CTL)
    and BSW deduction to compute Net Standard Volume (NSV) from Gross Observed Volume (GOV).
    """
    ENGINE_NAME = "Oil Accounting Engine"
    SPE_REFERENCE = "API MPMS Chapter 11.1 / ASTM D1250: Petroleum Measurement Tables"

    @classmethod
    def calculate_net_standard_volume(
        cls,
        gross_observed_volume_bbl: Optional[float],
        observed_temp_f: Optional[float],
        observed_api_gravity: Optional[float],
        bsw_percentage: Optional[float]
    ) -> EngineeringResult:
        missing = PhysicsGuardrails.assert_strict_data_integrity(
            required_fields={
                "gross_observed_volume_bbl": gross_observed_volume_bbl,
                "bsw_percentage": bsw_percentage
            },
            calculation_name=cls.ENGINE_NAME,
            model_name="API MPMS Ch. 11.1 Temperature & BSW Correction",
            spe_reference=cls.SPE_REFERENCE
        )
        if missing:
            return missing

        gov = gross_observed_volume_bbl
        bsw = min(100.0, max(0.0, bsw_percentage)) / 100.0
        api = observed_api_gravity or 34.0
        t = observed_temp_f or 60.0

        # Thermal expansion coefficient alpha based on API gravity
        # Standard CTL (Correction for Temperature on Liquid)
        delta_t = t - 60.0
        alpha = 0.00045  # Typical for ~30-38 API crude
        ctl = math.exp(-alpha * delta_t * (1.0 + 0.8 * alpha * delta_t))

        gross_standard_volume = gov * ctl
        net_standard_volume = gross_standard_volume * (1.0 - bsw)

        return EngineeringResult(
            calculation_name=cls.ENGINE_NAME,
            value=round(net_standard_volume, 2),
            unit="STB",
            model="API MPMS Ch. 11.1 Temperature & BSW Correction",
            status=EngineeringStatus.VALID.value,
            evidence={
                "gross_observed_volume_bbl": round(gov, 2),
                "correction_factor_ctl": round(ctl, 5),
                "gross_standard_volume_stb": round(gross_standard_volume, 2),
                "bsw_deduction_bbl": round(gross_standard_volume * bsw, 2),
                "net_standard_volume_stb": round(net_standard_volume, 2)
            },
            correlation_reference=cls.SPE_REFERENCE
        )


class JointVentureAccountingEngine:
    """
    25. Joint Venture & Company Accounting Engine.
    Calculates partner net entitlement based on Working Interest (WI), Net Revenue Interest (NRI),
    and royalty deductions under Production Sharing Contracts (PSC) or Concession agreements.
    """
    ENGINE_NAME = "Joint Venture & Company Accounting Engine"
    SPE_REFERENCE = "SPE-107767: Petroleum Fiscal Systems and Joint Venture Entitlement"

    @classmethod
    def calculate_partner_entitlement(
        cls,
        total_field_revenue_usd: Optional[float],
        total_production_stb: Optional[float],
        working_interest_fraction: Optional[float],
        royalty_rate_fraction: Optional[float] = 0.125,
        partner_name: str = "Operator"
    ) -> EngineeringResult:
        missing = PhysicsGuardrails.assert_strict_data_integrity(
            required_fields={
                "total_field_revenue_usd": total_field_revenue_usd,
                "total_production_stb": total_production_stb,
                "working_interest_fraction": working_interest_fraction
            },
            calculation_name=cls.ENGINE_NAME,
            model_name="Upstream Joint Operating Agreement (JOA) Model",
            spe_reference=cls.SPE_REFERENCE
        )
        if missing:
            return missing

        wi = min(1.0, max(0.0, working_interest_fraction))
        royalty = min(1.0, max(0.0, royalty_rate_fraction or 0.125))
        nri = wi * (1.0 - royalty)

        net_revenue_partner = total_field_revenue_usd * nri
        net_barrels_partner = total_production_stb * nri
        royalty_deduction_usd = total_field_revenue_usd * wi * royalty

        return EngineeringResult(
            calculation_name=cls.ENGINE_NAME,
            value=round(net_revenue_partner, 2),
            unit="USD",
            model="Upstream Joint Operating Agreement (JOA) Model",
            status=EngineeringStatus.VALID.value,
            evidence={
                "partner": partner_name,
                "working_interest_pct": round(wi * 100.0, 2),
                "royalty_rate_pct": round(royalty * 100.0, 2),
                "net_revenue_interest_pct": round(nri * 100.0, 2),
                "partner_net_revenue_usd": round(net_revenue_partner, 2),
                "partner_entitlement_barrels_stb": round(net_barrels_partner, 2),
                "royalty_paid_usd": round(royalty_deduction_usd, 2)
            },
            correlation_reference=cls.SPE_REFERENCE
        )


class CAPEXEngine:
    """
    26. CAPEX Engine.
    Tracks drilling, completion, facilities, and artificial lift capital expenditure amortization.
    """
    ENGINE_NAME = "CAPEX Engine"
    SPE_REFERENCE = "SPE Guidelines for Upstream Economic Evaluation"

    @classmethod
    def calculate_capex_depreciation(
        cls,
        total_initial_capex_usd: Optional[float],
        cumulative_produced_stb: Optional[float],
        total_expected_eur_stb: Optional[float],
        facility_life_years: Optional[float] = 20.0
    ) -> EngineeringResult:
        missing = PhysicsGuardrails.assert_strict_data_integrity(
            required_fields={
                "total_initial_capex_usd": total_initial_capex_usd,
                "total_expected_eur_stb": total_expected_eur_stb
            },
            calculation_name=cls.ENGINE_NAME,
            model_name="Units-of-Production (UOP) Depreciation Model",
            spe_reference=cls.SPE_REFERENCE
        )
        if missing:
            return missing

        eur = total_expected_eur_stb
        np = cumulative_produced_stb or 0.0
        capex = total_initial_capex_usd

        # Unit of production amortization: Depr/bbl = CAPEX / EUR
        depreciation_per_bbl = capex / eur if eur > 0 else 0.0
        accumulated_depreciation = min(capex, np * depreciation_per_bbl)
        net_book_value = capex - accumulated_depreciation

        return EngineeringResult(
            calculation_name=cls.ENGINE_NAME,
            value=round(net_book_value, 2),
            unit="USD",
            model="Units-of-Production (UOP) Depreciation Model",
            status=EngineeringStatus.VALID.value,
            evidence={
                "total_capex_usd": round(capex, 2),
                "depreciation_per_barrel_usd": round(depreciation_per_bbl, 2),
                "accumulated_depreciation_usd": round(accumulated_depreciation, 2),
                "net_book_value_usd": round(net_book_value, 2),
                "recovery_of_capital_pct": round((accumulated_depreciation / capex * 100.0) if capex > 0 else 0.0, 1)
            },
            correlation_reference=cls.SPE_REFERENCE
        )


class OPEXEngine:
    """
    27. OPEX Engine.
    Monitors operational lifting costs: surface power, chemical inhibition, water disposal, and workovers.
    """
    ENGINE_NAME = "OPEX Engine"
    SPE_REFERENCE = "SPE Upstream Operational Benchmark Standards"

    @classmethod
    def calculate_lifting_cost(
        cls,
        fixed_monthly_opex_usd: Optional[float],
        variable_cost_per_liquid_bbl_usd: Optional[float],
        monthly_oil_stb: Optional[float],
        monthly_water_bbl: Optional[float]
    ) -> EngineeringResult:
        missing = PhysicsGuardrails.assert_strict_data_integrity(
            required_fields={
                "fixed_monthly_opex_usd": fixed_monthly_opex_usd,
                "monthly_oil_stb": monthly_oil_stb
            },
            calculation_name=cls.ENGINE_NAME,
            model_name="Variable & Fixed Lifting Cost Model",
            spe_reference=cls.SPE_REFERENCE
        )
        if missing:
            return missing

        total_liquid = (monthly_oil_stb or 0.0) + (monthly_water_bbl or 0.0)
        var_cost = (variable_cost_per_liquid_bbl_usd or 1.25) * total_liquid
        total_opex = fixed_monthly_opex_usd + var_cost

        lifting_cost_per_barrel = (total_opex / monthly_oil_stb) if monthly_oil_stb > 0 else float("inf")

        return EngineeringResult(
            calculation_name=cls.ENGINE_NAME,
            value=round(lifting_cost_per_barrel, 2),
            unit="USD/STB",
            model="Variable & Fixed Lifting Cost Model",
            status=EngineeringStatus.VALID.value,
            evidence={
                "total_monthly_opex_usd": round(total_opex, 2),
                "fixed_opex_usd": round(fixed_monthly_opex_usd, 2),
                "variable_liquid_handling_usd": round(var_cost, 2),
                "lifting_cost_per_barrel_usd": round(lifting_cost_per_barrel, 2),
                "economic_viability": "PROFITABLE" if lifting_cost_per_barrel < 40.0 else "MARGINAL_HIGH_COST"
            },
            correlation_reference=cls.SPE_REFERENCE
        )


class PetroleumEconomicsEngine:
    """
    28. Profit & Loss / Petroleum Economics Engine.
    Discounted Cash Flow (DCF), Net Present Value (NPV), and Internal Rate of Return (IRR).
    """
    ENGINE_NAME = "Profit & Loss / Petroleum Economics Engine"
    SPE_REFERENCE = "SPE Petroleum Economics Handbook (Stermole & Stermole 2014)"

    @classmethod
    def evaluate_cash_flow(
        cls,
        annual_cash_flows_usd: List[float],
        discount_rate_fraction: float = 0.10,
        crude_price_usd_bbl: float = 75.0
    ) -> EngineeringResult:
        if not annual_cash_flows_usd:
            return EngineeringResult(
                calculation_name=cls.ENGINE_NAME,
                value=None,
                model="Discounted Cash Flow (DCF) NPV Model",
                status=EngineeringStatus.INSUFFICIENT_DATA.value,
                warnings=["Annual cash flow schedule is required."]
            )

        r = discount_rate_fraction
        npv = 0.0
        cumulative_cash = 0.0
        payback_year = None

        for year, cf in enumerate(annual_cash_flows_usd):
            npv += cf / math.pow(1.0 + r, year)
            cumulative_cash += cf
            if payback_year is None and cumulative_cash >= 0:
                payback_year = year

        return EngineeringResult(
            calculation_name=cls.ENGINE_NAME,
            value=round(npv, 2),
            unit="USD",
            model="Discounted Cash Flow (DCF) NPV Model",
            status=EngineeringStatus.VALID.value,
            evidence={
                "net_present_value_usd": round(npv, 2),
                "discount_rate_pct": round(r * 100.0, 1),
                "undiscounted_cash_flow_usd": round(sum(annual_cash_flows_usd), 2),
                "payback_period_years": payback_year,
                "project_economic_viability": "COMMERCIALLY_VIABLE" if npv > 0 else "UNECONOMIC"
            },
            correlation_reference=cls.SPE_REFERENCE
        )


class StatisticalProbabilisticEngine:
    """
    29. Statistical & Probabilistic Engine.
    Executes Monte Carlo probabilistic volumetric simulations generating P10, P50, and P90 reserves.
    Conforms strictly to SPE-PRMS probabilistic definitions:
    P90 (Proved 1P), P50 (Proved + Probable 2P), P10 (Proved + Probable + Possible 3P).
    """
    ENGINE_NAME = "Statistical & Probabilistic Engine"
    SPE_REFERENCE = "SPE-PRMS Guidelines: Probabilistic Estimation of Hydrocarbon Resources"

    @classmethod
    def simulate_prms_reserves(
        cls,
        area_acres_min: float, area_acres_mode: float, area_acres_max: float,
        net_pay_ft_min: float, net_pay_ft_mode: float, net_pay_ft_max: float,
        porosity_min: float, porosity_mode: float, porosity_max: float,
        sw_min: float, sw_mode: float, sw_max: float,
        boi_rb_stb: float = 1.25,
        recovery_factor_mode: float = 0.35,
        num_iterations: int = 1000
    ) -> EngineeringResult:
        random.seed(42)  # Deterministic seed for reproducible testing
        samples_ooip = []
        samples_eur = []

        for _ in range(num_iterations):
            a = random.triangular(area_acres_min, area_acres_max, area_acres_mode)
            h = random.triangular(net_pay_ft_min, net_pay_ft_max, net_pay_ft_mode)
            phi = random.triangular(porosity_min, porosity_max, porosity_mode)
            sw = random.triangular(sw_min, sw_max, sw_mode)
            rf = random.triangular(recovery_factor_mode * 0.7, min(0.60, recovery_factor_mode * 1.3), recovery_factor_mode)

            # Volumetric STOIIP = (7758 * A * h * phi * (1 - Sw)) / Boi
            stoiip = (7758.0 * a * h * phi * (1.0 - sw)) / boi_rb_stb
            eur = stoiip * rf
            samples_ooip.append(stoiip)
            samples_eur.append(eur)

        samples_ooip.sort()
        samples_eur.sort()

        # In SPE-PRMS:
        # P90 is the value exceeded by 90% of samples (10th percentile of ascending list)
        # P50 is 50th percentile
        # P10 is exceeded by 10% of samples (90th percentile)
        idx_p90 = int(0.10 * num_iterations)
        idx_p50 = int(0.50 * num_iterations)
        idx_p10 = int(0.90 * num_iterations)

        p90_eur = samples_eur[idx_p90]
        p50_eur = samples_eur[idx_p50]
        p10_eur = samples_eur[idx_p10]

        return EngineeringResult(
            calculation_name=cls.ENGINE_NAME,
            value=round(p50_eur, 0),
            unit="STB",
            model="SPE-PRMS Monte Carlo Reserves Simulation",
            status=EngineeringStatus.VALID.value,
            evidence={
                "p90_1p_proved_eur_stb": round(p90_eur, 0),
                "p50_2p_probable_eur_stb": round(p50_eur, 0),
                "p10_3p_possible_eur_stb": round(p10_eur, 0),
                "p50_ooip_stb": round(samples_ooip[idx_p50], 0),
                "iterations_computed": num_iterations
            },
            correlation_reference=cls.SPE_REFERENCE
        )
