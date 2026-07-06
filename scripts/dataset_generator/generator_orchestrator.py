"""
generator_orchestrator.py

Top-level entry point that wires every module together to produce a
complete synthetic UPI dataset:

    1. Generate and persist all master tables (bank, psp, mcc, purpose,
       response, error, initiation mode, mandate operation, recurrence).
    2. Generate and persist the customer and merchant masters.
    3. Generate one or more batches of fact_upi_transactions rows.
    4. Validate each batch with DatasetValidator; on failure, regenerate
       only that batch (up to a bounded retry count) rather than the
       whole run.
    5. Persist each valid batch to fact/fact_upi_transactions_batch_NNN.csv.

Run directly:  python generator_orchestrator.py
Configure scale by editing config.DEFAULT_CONFIG (or constructing a
GeneratorConfig with different ROWS_PER_BATCH / TOTAL_ROWS).
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import List

import constants
from config import GeneratorConfig, DEFAULT_CONFIG
from customer_generator import CustomerGenerator
from master_data_generator import MasterDataGenerator
from merchant_generator import MerchantGenerator
from transaction_generator import TransactionGenerator
from utils import write_dicts_to_csv
from validation_module import DatasetValidator, ValidationReport

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("generator_orchestrator")

MAX_BATCH_REGENERATION_ATTEMPTS = 3


class GeneratorOrchestrator:
    """Coordinates master-data generation, transaction generation, and validation."""

    def __init__(self, config: GeneratorConfig) -> None:
        self.config = config
        self.master_dir: Path = config.master_path()
        self.fact_dir: Path = config.fact_path()

    # ------------------------------------------------------------------
    # Master / entity data
    # ------------------------------------------------------------------
    def build_master_data(self) -> dict:
        """Generate and persist all reference master tables."""
        logger.info("Generating master reference tables ...")
        mdg = MasterDataGenerator(self.config)
        master_data = mdg.write_all(self.master_dir)
        logger.info(
            "Master tables written: %d banks, %d psps, %d mccs, %d purposes",
            len(master_data["bank_master"]),
            len(master_data["psp_master"]),
            len(master_data["mcc_master"]),
            len(master_data["purpose_master"]),
        )
        return master_data

    def build_customers(self, master_data: dict) -> list:
        logger.info("Generating customer master (%d customers) ...", self.config.NUMBER_OF_CUSTOMERS)
        gen = CustomerGenerator(self.config, master_data["bank_master"], master_data["psp_master"])
        customers = gen.write(self.master_dir)
        logger.info("Customer master written: %d rows", len(customers))
        return customers

    def build_merchants(self, master_data: dict) -> list:
        logger.info("Generating merchant master (%d merchants) ...", self.config.NUMBER_OF_MERCHANTS)
        gen = MerchantGenerator(self.config, master_data["bank_master"], master_data["psp_master"])
        merchants = gen.write(self.master_dir)
        logger.info("Merchant master written: %d rows", len(merchants))
        return merchants

    # ------------------------------------------------------------------
    # Validation wiring
    # ------------------------------------------------------------------
    def _build_validator(self, master_data: dict, banks: list, psps: list) -> DatasetValidator:
        return DatasetValidator(
            valid_banks={b.bank_name for b in banks},
            valid_psps={p.psp_name for p in psps},
            valid_mccs={m["mcc"] for m in master_data["mcc_master"]},
            valid_purposecodes={p["purposecode"] for p in master_data["purpose_master"]},
            valid_initiation_modes={i["initiationmode"] for i in master_data["initiation_mode_master"]},
            valid_response_codes={r["responsecode"] for r in master_data["response_master"]},
            valid_error_codes={e["errorcode"] for e in master_data["error_master"]},
        )

    # ------------------------------------------------------------------
    # Batch generation with validate / reject / regenerate
    # ------------------------------------------------------------------
    def _generate_validated_batch(
        self,
        batch_index: int,
        rows_target: int,
        master_data: dict,
        customers: list,
        merchants: list,
        validator: DatasetValidator,
    ) -> List[dict]:
        """Generate one batch, regenerating (with a fresh seed) on validation failure."""
        for attempt in range(1, MAX_BATCH_REGENERATION_ATTEMPTS + 1):
            attempt_seed = self.config.RANDOM_SEED + (batch_index * 1000) + attempt
            batch_config = GeneratorConfig(
                ROWS_PER_BATCH=self.config.ROWS_PER_BATCH,
                TOTAL_ROWS=self.config.TOTAL_ROWS,
                RANDOM_SEED=attempt_seed,
                OUTPUT_FOLDER=self.config.OUTPUT_FOLDER,
                MASTER_SUBDIR=self.config.MASTER_SUBDIR,
                FACT_SUBDIR=self.config.FACT_SUBDIR,
                START_DATE=self.config.START_DATE,
                END_DATE=self.config.END_DATE,
                NUMBER_OF_CUSTOMERS=self.config.NUMBER_OF_CUSTOMERS,
                NUMBER_OF_MERCHANTS=self.config.NUMBER_OF_MERCHANTS,
                NUMBER_OF_BANKS=self.config.NUMBER_OF_BANKS,
                NUMBER_OF_PSPS=self.config.NUMBER_OF_PSPS,
                SUCCESS_RATE=self.config.SUCCESS_RATE,
                FAILURE_RATE=self.config.FAILURE_RATE,
                AUTOPAY_TXN_SHARE=self.config.AUTOPAY_TXN_SHARE,
                MANDATE_CUSTOMER_SHARE=self.config.MANDATE_CUSTOMER_SHARE,
                MAX_EXECUTIONS_PER_MANDATE=self.config.MAX_EXECUTIONS_PER_MANDATE,
                MIN_EXECUTIONS_PER_MANDATE=self.config.MIN_EXECUTIONS_PER_MANDATE,
                API_DISTRIBUTION=self.config.API_DISTRIBUTION,
            )

            generator = TransactionGenerator(
                batch_config,
                master_data["bank_master"],
                master_data["psp_master"],
                customers,
                merchants,
            )
            rows = generator.generate_batch(rows_target)

            report: ValidationReport = validator.validate(rows)
            if report.is_valid:
                logger.info(
                    "Batch %03d valid on attempt %d: %d rows",
                    batch_index, attempt, len(rows),
                )
                return rows

            logger.warning(
                "Batch %03d attempt %d failed validation with %d error(s); regenerating.",
                batch_index, attempt, len(report.errors),
            )
            for err in report.errors[:10]:
                logger.warning("  - %s", err)

        raise RuntimeError(
            f"Batch {batch_index:03d} failed validation after "
            f"{MAX_BATCH_REGENERATION_ATTEMPTS} attempts."
        )

    # ------------------------------------------------------------------
    # Full run
    # ------------------------------------------------------------------
    def run(self) -> None:
        start_time = time.monotonic()
        logger.info(
            "Starting generation run: TOTAL_ROWS=%d ROWS_PER_BATCH=%d SEED=%d",
            self.config.TOTAL_ROWS, self.config.ROWS_PER_BATCH, self.config.RANDOM_SEED,
        )

        master_data = self.build_master_data()
        customers = self.build_customers(master_data)
        merchants = self.build_merchants(master_data)
        validator = self._build_validator(master_data, master_data["bank_master"], master_data["psp_master"])

        num_batches = self.config.number_of_batches()
        rows_remaining = self.config.TOTAL_ROWS
        total_written = 0

        for batch_index in range(1, num_batches + 1):
            rows_target = min(self.config.ROWS_PER_BATCH, rows_remaining)
            if rows_target <= 0:
                break

            rows = self._generate_validated_batch(
                batch_index, rows_target, master_data, customers, merchants, validator
            )

            out_path = self.fact_dir / f"fact_upi_transactions_batch_{batch_index:03d}.csv"
            write_dicts_to_csv(out_path, rows, constants.FACT_TABLE_FIELDS)
            logger.info("Wrote %d rows to %s", len(rows), out_path)

            total_written += len(rows)
            rows_remaining -= rows_target

        elapsed = time.monotonic() - start_time
        logger.info(
            "Generation complete: %d total rows across %d batch(es) in %.2fs",
            total_written, num_batches, elapsed,
        )


def main() -> None:
    """Entry point for running the full generator with DEFAULT_CONFIG."""
    orchestrator = GeneratorOrchestrator(DEFAULT_CONFIG)
    orchestrator.run()


if __name__ == "__main__":
    main()
