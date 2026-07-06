"""
merchant_generator.py

Generates the Merchant Master. Every merchant has a fixed MCC, name,
genre, merchant type, onboarding type, verified name, and PSP/bank
pairing that never change across transactions (Rule: Merchant Consistency).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from random import Random
from typing import List

import constants
from config import GeneratorConfig
from master_data_generator import BankRecord, PspRecord
from utils import build_vpa, derive_sub_seed, seeded_random, write_dataclasses_to_csv

MERCHANT_NAME_POOL: tuple[str, ...] = (
    "BigBasket", "Zomato", "Swiggy", "Amazon Retail", "Flipkart", "Netflix India",
    "Hotstar", "Spotify India", "Airtel", "Jio", "Vodafone Idea", "Tata Power",
    "Adani Electricity", "Apollo Hospitals", "Fortis Healthcare", "Byju's",
    "Unacademy", "IRCTC", "MakeMyTrip", "OYO Rooms", "Reliance Digital",
    "Croma", "Lifestyle Stores", "Shoppers Stop", "HDFC Life Insurance",
    "ICICI Lombard", "LIC of India", "Groww", "Zerodha", "HDFC Mutual Fund",
    "Urban Company", "BookMyShow", "PVR Cinemas", "Domino's Pizza",
    "McDonald's India", "Starbucks India", "Café Coffee Day", "Decathlon",
    "IKEA India", "Nykaa", "Myntra", "Practo", "1mg", "PharmEasy",
    "Delhivery", "Blinkit", "Zepto", "Licious", "Country Delight",
    "Bounce Rentals",
)

# Weight merchant category selection so that AutoPay-heavy categories
# (utilities, telecom, OTT, insurance) get proportionally more merchants,
# matching real-world PSP AutoPay adoption patterns.
MCC_SELECTION_WEIGHTS: dict[str, float] = {
    "4899": 3.0, "4814": 4.0, "4900": 3.0, "6300": 2.5, "8062": 1.5,
    "8220": 1.0, "8211": 1.0, "6051": 2.0, "7372": 2.5, "7841": 2.5,
    "6513": 1.0, "5964": 3.0, "5999": 4.0, "7011": 1.5, "4511": 1.0,
    "5541": 2.0, "6011": 0.5, "4121": 2.0, "4111": 1.0, "5411": 4.0,
    "5812": 4.0, "5813": 1.5, "5912": 2.0, "5311": 1.5, "5732": 1.5,
    "5691": 1.5, "5261": 0.5, "8398": 0.5, "8011": 1.0, "4131": 0.5,
}


@dataclass(frozen=True)
class MerchantRecord:
    merchant_id: str
    merchant_name: str
    verified_name: str
    mcc: str
    merchant_type: str
    merchant_genre: str
    onboarding_type: str
    payeeaddress: str
    payeepsp: str
    payeepsporgid: str
    payeebank: str


class MerchantGenerator:
    """Builds a deterministic, internally consistent Merchant Master."""

    def __init__(self, config: GeneratorConfig, banks: List[BankRecord], psps: List[PspRecord]) -> None:
        self.config = config
        self.banks = banks
        self.psps = psps
        self.rng: Random = seeded_random(derive_sub_seed(config.RANDOM_SEED, "merchant_generator"))

    def generate(self) -> List[MerchantRecord]:
        """Generate NUMBER_OF_MERCHANTS distinct, stable merchant identities."""
        mccs = [m["mcc"] for m in constants.MCC_LIST]
        weights = [MCC_SELECTION_WEIGHTS.get(mcc, 1.0) for mcc in mccs]

        merchants: List[MerchantRecord] = []
        for idx in range(self.config.NUMBER_OF_MERCHANTS):
            base_name = MERCHANT_NAME_POOL[idx % len(MERCHANT_NAME_POOL)]
            disambiguator = "" if idx < len(MERCHANT_NAME_POOL) else f" {idx // len(MERCHANT_NAME_POOL) + 1}"
            name = f"{base_name}{disambiguator}"
            verified_name = f"{name} Pvt Ltd" if self.rng.random() < 0.6 else name

            mcc = self.rng.choices(mccs, weights=weights, k=1)[0]
            genre = self.rng.choices(
                constants.MERCHANT_GENRES, weights=[50, 30, 20], k=1
            )[0]
            merchant_type = self.rng.choices(
                constants.MERCHANT_TYPES, weights=[30, 50, 20], k=1
            )[0]
            onboarding = self.rng.choice(constants.ONBOARDING_TYPES)

            psp = self.rng.choice(self.psps)
            bank = self.rng.choice(self.banks)
            local_part = "".join(ch for ch in base_name.lower() if ch.isalnum()) + str(idx)
            vpa = build_vpa(local_part, psp.handle.lower())

            merchants.append(
                MerchantRecord(
                    merchant_id=f"MER{idx + 1:06d}",
                    merchant_name=name,
                    verified_name=verified_name,
                    mcc=mcc,
                    merchant_type=merchant_type,
                    merchant_genre=genre,
                    onboarding_type=onboarding,
                    payeeaddress=vpa,
                    payeepsp=psp.psp_name,
                    payeepsporgid=psp.orgid,
                    payeebank=bank.bank_name,
                )
            )
        return merchants

    def write(self, master_dir: Path) -> List[MerchantRecord]:
        """Generate the merchant master and persist it to CSV."""
        merchants = self.generate()
        write_dataclasses_to_csv(master_dir / "merchant_master.csv", merchants)
        return merchants


if __name__ == "__main__":
    from config import DEFAULT_CONFIG
    from master_data_generator import MasterDataGenerator

    mdg = MasterDataGenerator(DEFAULT_CONFIG)
    master_data = mdg.write_all(DEFAULT_CONFIG.master_path())
    gen = MerchantGenerator(DEFAULT_CONFIG, master_data["bank_master"], master_data["psp_master"])
    gen.write(DEFAULT_CONFIG.master_path())
    print("Merchant master generated.")
