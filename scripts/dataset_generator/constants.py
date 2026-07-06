"""
constants.py

Static, official reference values used across the generator.
These are the authoritative code lists — no other module invents values
outside of what is defined here.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# API lifecycle — the ONLY 12 valid API names
# ---------------------------------------------------------------------------
API_NAMES: tuple[str, ...] = (
    "ReqMandate",
    "RespMandate",
    "ReqAuthMandate",
    "RespAuthMandate",
    "ReqMandateConfirmation",
    "RespMandateConfirmation",
    "ReqValCust",
    "RespValCust",
    "ReqAuthValCust",
    "RespAuthValCust",
    "ReqPay",
    "RespPay",
)

# Request -> Response pairing
REQUEST_RESPONSE_PAIRS: dict[str, str] = {
    "ReqMandate": "RespMandate",
    "ReqAuthMandate": "RespAuthMandate",
    "ReqMandateConfirmation": "RespMandateConfirmation",
    "ReqValCust": "RespValCust",
    "ReqAuthValCust": "RespAuthValCust",
    "ReqPay": "RespPay",
}
RESPONSE_TO_REQUEST: dict[str, str] = {v: k for k, v in REQUEST_RESPONSE_PAIRS.items()}

# Full mandate lifecycle order (used for timestamp ordering / sequencing)
MANDATE_LIFECYCLE_ORDER: tuple[str, ...] = (
    "ReqMandate",
    "RespMandate",
    "ReqAuthMandate",
    "RespAuthMandate",
    "ReqMandateConfirmation",
    "RespMandateConfirmation",
    "ReqValCust",
    "RespValCust",
    "ReqPay",
    "RespPay",
)

FINANCIAL_APIS: frozenset[str] = frozenset({"ReqPay", "RespPay"})
NON_FINANCIAL_APIS: frozenset[str] = frozenset(API_NAMES) - FINANCIAL_APIS

TXN_TYPE_FINANCIAL = "Financial"
TXN_TYPE_NON_FINANCIAL = "NonFinancial"

# ---------------------------------------------------------------------------
# Mandate Operation Master
# ---------------------------------------------------------------------------
MANDATE_OPERATIONS: tuple[str, ...] = ("CREATE", "UPDATE", "PAUSE", "UNPAUSE", "REVOKE")

# ---------------------------------------------------------------------------
# Recurrence Pattern Master
# ---------------------------------------------------------------------------
RECURRENCE_PATTERNS: tuple[str, ...] = (
    "DAILY",
    "WEEKLY",
    "FORTNIGHTLY",
    "MONTHLY",
    "BIMONTHLY",
    "QUARTERLY",
    "YEARLY",
    "ASPRESENTED",
)

# ---------------------------------------------------------------------------
# Initiation Mode Master (code -> attributes)
# ---------------------------------------------------------------------------
INITIATION_MODES: tuple[dict, ...] = (
    {"initiationmode": "00", "description": "Default", "category": "Default", "autopay_supported": "N"},
    {"initiationmode": "01", "description": "Static QR Code", "category": "QR", "autopay_supported": "N"},
    {"initiationmode": "02", "description": "Static Secure QR Code", "category": "QR", "autopay_supported": "N"},
    {"initiationmode": "03", "description": "Bharat QR Code", "category": "QR", "autopay_supported": "N"},
    {"initiationmode": "04", "description": "Intent", "category": "Intent", "autopay_supported": "N"},
    {"initiationmode": "05", "description": "Secure Intent", "category": "Intent", "autopay_supported": "N"},
    {"initiationmode": "06", "description": "NFC (Near Field Communication)", "category": "Contactless", "autopay_supported": "N"},
    {"initiationmode": "07", "description": "BLE (Bluetooth Low Energy)", "category": "Contactless", "autopay_supported": "N"},
    {"initiationmode": "08", "description": "UHF (Ultra High Frequency)", "category": "Contactless", "autopay_supported": "N"},
    {"initiationmode": "09", "description": "Aadhaar", "category": "Aadhaar", "autopay_supported": "N"},
    {"initiationmode": "10", "description": "SDK (Software Development Kit)", "category": "SDK", "autopay_supported": "N"},
    {"initiationmode": "11", "description": "UPI-Mandate", "category": "Mandate", "autopay_supported": "Y"},
    {"initiationmode": "12", "description": "FIR (Foreign Inward Remittance)", "category": "International", "autopay_supported": "N"},
    {"initiationmode": "13", "description": "Static QR Mandate", "category": "QR Mandate", "autopay_supported": "Y"},
    {"initiationmode": "14", "description": "Bill Payment", "category": "BBPS", "autopay_supported": "Y"},
    {"initiationmode": "15", "description": "Dynamic QR Code", "category": "QR", "autopay_supported": "N"},
    {"initiationmode": "16", "description": "Dynamic Secure QR Code", "category": "QR", "autopay_supported": "N"},
    {"initiationmode": "17", "description": "Dynamic Secure QR Code Mandate", "category": "QR Mandate", "autopay_supported": "Y"},
    {"initiationmode": "18", "description": "Dynamic ATM", "category": "ATM", "autopay_supported": "N"},
    {"initiationmode": "19", "description": "Static QR Code", "category": "QR", "autopay_supported": "N"},
    {"initiationmode": "20", "description": "Static Secure QR Code", "category": "QR", "autopay_supported": "N"},
    {"initiationmode": "21", "description": "Static QR Mandate", "category": "QR Mandate", "autopay_supported": "Y"},
    {"initiationmode": "22", "description": "Dynamic QR Code", "category": "QR", "autopay_supported": "N"},
    {"initiationmode": "23", "description": "Dynamic Secure QR Code", "category": "QR", "autopay_supported": "N"},
    {"initiationmode": "24", "description": "Dynamic Secure QR Code Mandate", "category": "QR Mandate", "autopay_supported": "Y"},
    {"initiationmode": "25", "description": "CC Bill Payment for Self", "category": "Credit Card", "autopay_supported": "N"},
    {"initiationmode": "26", "description": "CC Bill Payment for Others", "category": "Credit Card", "autopay_supported": "N"},
    {"initiationmode": "27", "description": "Self Payments for NCMC", "category": "NCMC", "autopay_supported": "N"},
    {"initiationmode": "28", "description": "Other Payments for NCMC", "category": "NCMC", "autopay_supported": "N"},
    {"initiationmode": "31", "description": "UPI 123Pay", "category": "Feature Phone", "autopay_supported": "N"},
    {"initiationmode": "32", "description": "Connected Cars", "category": "IoT", "autopay_supported": "N"},
    {"initiationmode": "33", "description": "Embedded Payment", "category": "Embedded", "autopay_supported": "N"},
    {"initiationmode": "34", "description": "Embedded Autopay", "category": "Embedded AutoPay", "autopay_supported": "Y"},
    {"initiationmode": "35", "description": "Embedded OTM", "category": "Embedded", "autopay_supported": "N"},
    {"initiationmode": "46", "description": "Global Acceptance Proprietary QR Code", "category": "International QR", "autopay_supported": "N"},
    {"initiationmode": "47", "description": "Global Acceptance Secure QR Code", "category": "International QR", "autopay_supported": "N"},
    {"initiationmode": "48", "description": "Global Acceptance Non-Secure QR Code", "category": "International QR", "autopay_supported": "N"},
    {"initiationmode": "49", "description": "Global Acceptance Secure Intent", "category": "International Intent", "autopay_supported": "N"},
    {"initiationmode": "50", "description": "Global Acceptance Non-Secure Intent", "category": "International Intent", "autopay_supported": "N"},
)

MANDATE_CAPABLE_INITIATION_MODES: tuple[str, ...] = (
    "11", "13", "17", "21", "24", "34",
)
INTERNATIONAL_INITIATION_MODES: tuple[str, ...] = ("12", "46", "47", "48", "49", "50")
QR_INITIATION_MODES: tuple[str, ...] = ("01", "02", "03", "15", "16", "19", "20", "22", "23")

# ---------------------------------------------------------------------------
# Purpose Master (code -> attributes)
# ---------------------------------------------------------------------------
PURPOSE_CODES: tuple[dict, ...] = (
    {"purposecode": "00", "purpose": "Default", "category": "General", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "01", "purpose": "SEBI", "category": "Investments", "autopay_potential": "High", "recurring": "Y"},
    {"purposecode": "02", "purpose": "AMC", "category": "Investments", "autopay_potential": "High", "recurring": "Y"},
    {"purposecode": "03", "purpose": "Travel", "category": "Travel", "autopay_potential": "Medium", "recurring": "N"},
    {"purposecode": "04", "purpose": "Hospitality", "category": "Hospitality", "autopay_potential": "Medium", "recurring": "N"},
    {"purposecode": "05", "purpose": "Hospital", "category": "Healthcare", "autopay_potential": "High", "recurring": "Y"},
    {"purposecode": "06", "purpose": "Telecom", "category": "Telecom", "autopay_potential": "High", "recurring": "Y"},
    {"purposecode": "07", "purpose": "Insurance", "category": "Insurance", "autopay_potential": "High", "recurring": "Y"},
    {"purposecode": "08", "purpose": "Education", "category": "Education", "autopay_potential": "High", "recurring": "Y"},
    {"purposecode": "09", "purpose": "Gifting", "category": "Retail", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "10", "purpose": "BBPS", "category": "Bill Payments", "autopay_potential": "High", "recurring": "Y"},
    {"purposecode": "11", "purpose": "Global UPI", "category": "Cross Border", "autopay_potential": "Medium", "recurring": "N"},
    {"purposecode": "12", "purpose": "Metro ATM QR", "category": "ATM", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "13", "purpose": "Non-Metro ATM QR", "category": "ATM", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "14", "purpose": "SI (Standing Instruction)", "category": "AutoPay", "autopay_potential": "Very High", "recurring": "Y"},
    {"purposecode": "15", "purpose": "Corporate Disbursement", "category": "Corporate", "autopay_potential": "Medium", "recurring": "N"},
    {"purposecode": "17", "purpose": "P2P e-RUPI", "category": "e-RUPI", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "18", "purpose": "Govt B2C e-RUPI", "category": "Government", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "19", "purpose": "Private B2C e-RUPI", "category": "e-RUPI", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "20", "purpose": "B2B Business Payments", "category": "Business", "autopay_potential": "Medium", "recurring": "N"},
    {"purposecode": "25", "purpose": "Govt Securities through RBI Direct Scheme", "category": "Investments", "autopay_potential": "Medium", "recurring": "N"},
    {"purposecode": "41", "purpose": "UPI Lite Enablement & Add Money", "category": "UPI Lite", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "42", "purpose": "UPI Lite Topup", "category": "UPI Lite", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "43", "purpose": "UPI Lite Disablement", "category": "UPI Lite", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "44", "purpose": "UPI Lite Payment (Online)", "category": "UPI Lite", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "45", "purpose": "UPI Lite Payment (Offline)", "category": "UPI Lite", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "46", "purpose": "Transfer Out Functionality", "category": "UPI Lite", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "47", "purpose": "Lite Balance Above 2K Credit to CASA", "category": "UPI Lite", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "48", "purpose": "NIPL FIR", "category": "International", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "49", "purpose": "NIPL FOR", "category": "International", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "50", "purpose": "UPI Lite (Zero Balance Disablement)", "category": "UPI Lite", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "57", "purpose": "UPI Tap & Pay (User Registration)", "category": "Tap & Pay", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "58", "purpose": "UPI Tap & Pay (Merchant Registration)", "category": "Tap & Pay", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "59", "purpose": "Delegate Payments (Partial Delegation)", "category": "Delegate Payments", "autopay_potential": "Medium", "recurring": "Y"},
    {"purposecode": "60", "purpose": "NIPL Reverse Acceptance Model", "category": "International", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "61", "purpose": "Indirect QR Scan & Pay (FCY)", "category": "Cross Border", "autopay_potential": "Medium", "recurring": "N"},
    {"purposecode": "62", "purpose": "Direct QR Scan & Pay (FCY)", "category": "Cross Border", "autopay_potential": "Medium", "recurring": "N"},
    {"purposecode": "63", "purpose": "Indirect QR Scan & Pay (DCC)", "category": "Cross Border", "autopay_potential": "Medium", "recurring": "N"},
    {"purposecode": "64", "purpose": "Direct QR Scan & Pay (DCC)", "category": "Cross Border", "autopay_potential": "Medium", "recurring": "N"},
    {"purposecode": "65", "purpose": "Direct INR", "category": "Cross Border", "autopay_potential": "Medium", "recurring": "N"},
    {"purposecode": "66", "purpose": "Indirect INR", "category": "Cross Border", "autopay_potential": "Medium", "recurring": "N"},
    {"purposecode": "67", "purpose": "Intl AutoPay", "category": "International AutoPay", "autopay_potential": "High", "recurring": "Y"},
    {"purposecode": "68", "purpose": "Intl AutoPay", "category": "International AutoPay", "autopay_potential": "High", "recurring": "Y"},
    {"purposecode": "69", "purpose": "Intl AutoPay", "category": "International AutoPay", "autopay_potential": "High", "recurring": "Y"},
    {"purposecode": "70", "purpose": "Intl AutoPay", "category": "International AutoPay", "autopay_potential": "High", "recurring": "Y"},
    {"purposecode": "71", "purpose": "Lite AutoPay", "category": "AutoPay", "autopay_potential": "High", "recurring": "Y"},
    {"purposecode": "72", "purpose": "Financial Transaction API (ReqPay) during EMI", "category": "EMI", "autopay_potential": "High", "recurring": "Y"},
    {"purposecode": "73", "purpose": "Intl AutoPay", "category": "International AutoPay", "autopay_potential": "High", "recurring": "Y"},
    {"purposecode": "74", "purpose": "Intl AutoPay", "category": "International AutoPay", "autopay_potential": "High", "recurring": "Y"},
    {"purposecode": "75", "purpose": "Intl AutoPay", "category": "International AutoPay", "autopay_potential": "High", "recurring": "Y"},
    {"purposecode": "76", "purpose": "Securities Brokers & Dealers", "category": "Investments", "autopay_potential": "High", "recurring": "Y"},
    {"purposecode": "77", "purpose": "Online Merchants", "category": "E-Commerce", "autopay_potential": "Medium", "recurring": "N"},
    {"purposecode": "78", "purpose": "Reserved for Future (UPI Mandates)", "category": "Reserved", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "79", "purpose": "Reserved for Future (UPI Mandates)", "category": "Reserved", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "80", "purpose": "New User Activation for Lite X", "category": "UPI Lite X", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "81", "purpose": "Deactivation for Lite X", "category": "UPI Lite X", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "82", "purpose": "UPI Lite AutoPay", "category": "AutoPay", "autopay_potential": "High", "recurring": "Y"},
    {"purposecode": "83", "purpose": "Embedded Payments", "category": "Embedded Payments", "autopay_potential": "Medium", "recurring": "N"},
    {"purposecode": "84", "purpose": "ICD using UPI for Self Account", "category": "Deposit Banking", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "85", "purpose": "ICD using UPI for Third Party", "category": "Deposit Banking", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "86", "purpose": "UPI 123PAY Transaction", "category": "UPI 123PAY", "autopay_potential": "Medium", "recurring": "N"},
    {"purposecode": "87", "purpose": "Delegate Payments (Full Delegation)", "category": "Delegate Payments", "autopay_potential": "High", "recurring": "Y"},
    {"purposecode": "88", "purpose": "UPI on Web", "category": "UPI Web", "autopay_potential": "Medium", "recurring": "N"},
    {"purposecode": "92", "purpose": "UPI QR using Digital Rupee", "category": "CBDC", "autopay_potential": "Medium", "recurring": "N"},
    {"purposecode": "A1", "purpose": "Govt B2C e-RUPI", "category": "Government", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "AK", "purpose": "Pay by Points", "category": "Loyalty", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "AV", "purpose": "Business Payments via UPI (Multi-Signatory CA)", "category": "Business Payments", "autopay_potential": "Medium", "recurring": "N"},
    {"purposecode": "AW", "purpose": "Business Payments via UPI (Sole Prop CA)", "category": "Business Payments", "autopay_potential": "Medium", "recurring": "N"},
    {"purposecode": "AX", "purpose": "RuPay Corporate Credit Cards on UPI", "category": "Corporate Cards", "autopay_potential": "Medium", "recurring": "N"},
    {"purposecode": "AY", "purpose": "Mandates for Business Payments / Mandate Migration", "category": "Business AutoPay", "autopay_potential": "Very High", "recurring": "Y"},
    {"purposecode": "BC", "purpose": "UPI Tap & Pay (P2M Lite Payment without ARPC)", "category": "Tap & Pay", "autopay_potential": "Medium", "recurring": "N"},
    {"purposecode": "BD", "purpose": "PACB (Cross Border Payment Aggregator) Transactions", "category": "Cross Border", "autopay_potential": "Medium", "recurring": "N"},
    {"purposecode": "BB", "purpose": "PACB Mandate", "category": "Cross Border AutoPay", "autopay_potential": "High", "recurring": "Y"},
    {"purposecode": "BE", "purpose": "BBPS FX", "category": "BBPS", "autopay_potential": "Medium", "recurring": "N"},
    {"purposecode": "BH", "purpose": "IoT Payments", "category": "IoT", "autopay_potential": "High", "recurring": "Y"},
    {"purposecode": "BR", "purpose": "OS Native Biometrics for Pay Authentication", "category": "Authentication", "autopay_potential": "Low", "recurring": "N"},
    {"purposecode": "BS", "purpose": "UPI Tap & Pay No-CVM Transaction on POS", "category": "Tap & Pay", "autopay_potential": "Medium", "recurring": "N"},
    {"purposecode": "BT", "purpose": "Step-Up Authentication", "category": "Authentication", "autopay_potential": "Low", "recurring": "N"},
)

RECURRING_PURPOSE_CODES: tuple[str, ...] = tuple(
    p["purposecode"] for p in PURPOSE_CODES if p["recurring"] == "Y"
)
NON_RECURRING_PURPOSE_CODES: tuple[str, ...] = tuple(
    p["purposecode"] for p in PURPOSE_CODES if p["recurring"] == "N"
)

# ---------------------------------------------------------------------------
# Response Code Master
# ---------------------------------------------------------------------------
RESPONSE_CODES: tuple[dict, ...] = (
    {"responsecode": "00", "responseresult": "SUCCESS", "description": "Transaction Successful", "owner": "NPCI", "retryable": "N"},
    {"responsecode": "U69", "responseresult": "FAILURE", "description": "Transaction failed at Payer PSP", "owner": "PayerPSP", "retryable": "Y"},
    {"responsecode": "U30", "responseresult": "FAILURE", "description": "Format error at Issuer", "owner": "IssuerBank", "retryable": "N"},
    {"responsecode": "U16", "responseresult": "FAILURE", "description": "Insufficient funds", "owner": "IssuerBank", "retryable": "N"},
    {"responsecode": "U17", "responseresult": "FAILURE", "description": "Invalid MPIN", "owner": "PayerPSP", "retryable": "Y"},
    {"responsecode": "U67", "responseresult": "FAILURE", "description": "Beneficiary bank unavailable", "owner": "AcquirerBank", "retryable": "Y"},
    {"responsecode": "U68", "responseresult": "FAILURE", "description": "Payee PSP timeout", "owner": "PayeePSP", "retryable": "Y"},
    {"responsecode": "Z9", "responseresult": "FAILURE", "description": "NPCI switch timeout", "owner": "NPCI", "retryable": "Y"},
    {"responsecode": "U90", "responseresult": "FAILURE", "description": "Remitter bank system unavailable", "owner": "IssuerBank", "retryable": "Y"},
    {"responsecode": "U53", "responseresult": "FAILURE", "description": "Duplicate transaction", "owner": "NPCI", "retryable": "N"},
    {"responsecode": "U54", "responseresult": "FAILURE", "description": "Debit failed, credit not attempted", "owner": "IssuerBank", "retryable": "N"},
)
SUCCESS_RESPONSE_CODE = "00"
FAILURE_RESPONSE_CODES: tuple[str, ...] = tuple(
    r["responsecode"] for r in RESPONSE_CODES if r["responseresult"] == "FAILURE"
)

# ---------------------------------------------------------------------------
# Error Code Master (populated only for failed transactions)
# ---------------------------------------------------------------------------
ERROR_CODES: tuple[dict, ...] = (
    {"errorcode": "E001", "description": "Insufficient balance in account", "owner": "IssuerBank", "severity": "HIGH"},
    {"errorcode": "E002", "description": "Invalid credentials / MPIN mismatch", "owner": "PayerPSP", "severity": "MEDIUM"},
    {"errorcode": "E003", "description": "Beneficiary bank timeout", "owner": "AcquirerBank", "severity": "HIGH"},
    {"errorcode": "E004", "description": "NPCI switch unavailable", "owner": "NPCI", "severity": "CRITICAL"},
    {"errorcode": "E005", "description": "Duplicate transaction reference", "owner": "NPCI", "severity": "LOW"},
    {"errorcode": "E006", "description": "Payee PSP could not process request", "owner": "PayeePSP", "severity": "MEDIUM"},
    {"errorcode": "E007", "description": "Remitter core banking system down", "owner": "IssuerBank", "severity": "CRITICAL"},
    {"errorcode": "E008", "description": "Debit reversed due to credit failure", "owner": "IssuerBank", "severity": "HIGH"},
)

RESPONSE_TO_ERROR_MAP: dict[str, tuple[str, ...]] = {
    "U69": ("E002",),
    "U30": ("E002",),
    "U16": ("E001",),
    "U17": ("E002",),
    "U67": ("E003",),
    "U68": ("E006",),
    "Z9": ("E004",),
    "U90": ("E007",),
    "U53": ("E005",),
    "U54": ("E008",),
}

# ---------------------------------------------------------------------------
# Account type / payee type / onboarding / credit-info official values
# ---------------------------------------------------------------------------
ACCOUNT_TYPES: tuple[str, ...] = ("SAVINGS", "CURRENT", "OD", "CC", "PPI", "NRE", "NRO")
PAYEE_TYPES: tuple[str, ...] = ("PERSON", "MERCHANT")
MERCHANT_GENRES: tuple[str, ...] = ("SMALL", "LARGE", "AGGREGATOR")
MERCHANT_TYPES: tuple[str, ...] = ("OFFLINE", "ONLINE", "HYBRID")
ONBOARDING_TYPES: tuple[str, ...] = ("APP", "AGGREGATOR", "BANK", "PSP")
INITIATED_BY_VALUES: tuple[str, ...] = ("PAYER", "PAYEE")
CRED_TYPES: tuple[str, ...] = ("PIN", "OTP", "BIOMETRIC")
CRED_SUBTYPES: dict[str, tuple[str, ...]] = {
    "PIN": ("MPIN", "UPIN"),
    "OTP": ("SMS_OTP", "APP_OTP"),
    "BIOMETRIC": ("FINGERPRINT", "FACE"),
}
CURR_STATUS_DESCRIPTIONS: dict[str, str] = {
    "PENDING": "Transaction initiated, awaiting response",
    "COMPLETED": "Transaction completed successfully",
    "FAILED": "Transaction failed",
    "REVOKED": "Mandate revoked",
    "PAUSED": "Mandate paused",
}

# ---------------------------------------------------------------------------
# MCC Master — official-style MCC list used for Indian merchant categories
# ---------------------------------------------------------------------------
MCC_LIST: tuple[dict, ...] = (
    {"mcc": "5411", "category": "Grocery Stores/Supermarkets", "autopay_possible": "N", "autopay_priority": "LOW"},
    {"mcc": "5812", "category": "Restaurants", "autopay_possible": "N", "autopay_priority": "LOW"},
    {"mcc": "5813", "category": "Bars/Lounges", "autopay_possible": "N", "autopay_priority": "LOW"},
    {"mcc": "5912", "category": "Pharmacies", "autopay_possible": "N", "autopay_priority": "LOW"},
    {"mcc": "5311", "category": "Department Stores", "autopay_possible": "N", "autopay_priority": "LOW"},
    {"mcc": "5732", "category": "Electronics Stores", "autopay_possible": "N", "autopay_priority": "LOW"},
    {"mcc": "4121", "category": "Taxi/Rideshare", "autopay_possible": "N", "autopay_priority": "LOW"},
    {"mcc": "4111", "category": "Local Transit", "autopay_possible": "N", "autopay_priority": "LOW"},
    {"mcc": "4899", "category": "Cable/Satellite/DTH", "autopay_possible": "Y", "autopay_priority": "HIGH"},
    {"mcc": "4814", "category": "Telecom Services", "autopay_possible": "Y", "autopay_priority": "HIGH"},
    {"mcc": "4900", "category": "Utilities (Electricity/Water/Gas)", "autopay_possible": "Y", "autopay_priority": "HIGH"},
    {"mcc": "6300", "category": "Insurance", "autopay_possible": "Y", "autopay_priority": "HIGH"},
    {"mcc": "8011", "category": "Doctors/Physicians", "autopay_possible": "N", "autopay_priority": "LOW"},
    {"mcc": "8062", "category": "Hospitals", "autopay_possible": "Y", "autopay_priority": "MEDIUM"},
    {"mcc": "8220", "category": "Colleges/Universities", "autopay_possible": "Y", "autopay_priority": "MEDIUM"},
    {"mcc": "8211", "category": "Schools", "autopay_possible": "Y", "autopay_priority": "MEDIUM"},
    {"mcc": "5964", "category": "E-Commerce (Direct Marketing)", "autopay_possible": "N", "autopay_priority": "LOW"},
    {"mcc": "5999", "category": "Miscellaneous Retail", "autopay_possible": "N", "autopay_priority": "LOW"},
    {"mcc": "7011", "category": "Hotels/Lodging", "autopay_possible": "N", "autopay_priority": "LOW"},
    {"mcc": "4511", "category": "Airlines", "autopay_possible": "N", "autopay_priority": "LOW"},
    {"mcc": "5541", "category": "Fuel Stations", "autopay_possible": "N", "autopay_priority": "LOW"},
    {"mcc": "6011", "category": "ATM/Financial Institutions", "autopay_possible": "N", "autopay_priority": "LOW"},
    {"mcc": "6051", "category": "Investment/Mutual Funds", "autopay_possible": "Y", "autopay_priority": "HIGH"},
    {"mcc": "7372", "category": "Software/SaaS Subscriptions", "autopay_possible": "Y", "autopay_priority": "HIGH"},
    {"mcc": "7841", "category": "OTT/Streaming Services", "autopay_possible": "Y", "autopay_priority": "HIGH"},
    {"mcc": "5691", "category": "Apparel/Clothing", "autopay_possible": "N", "autopay_priority": "LOW"},
    {"mcc": "5261", "category": "Nurseries/Lawn/Garden", "autopay_possible": "N", "autopay_priority": "LOW"},
    {"mcc": "8398", "category": "Charitable/Social Services", "autopay_possible": "N", "autopay_priority": "LOW"},
    {"mcc": "6513", "category": "Real Estate/Rent", "autopay_possible": "Y", "autopay_priority": "MEDIUM"},
    {"mcc": "4131", "category": "Bus Lines", "autopay_possible": "N", "autopay_priority": "LOW"},
)

# ---------------------------------------------------------------------------
# Canonical fact_upi_transactions column order — MUST NOT be reordered,
# renamed, added to, or removed from. Sourced verbatim from SDS.pdf.
# ---------------------------------------------------------------------------
FACT_TABLE_FIELDS: tuple[str, ...] = (
    "apiname",
    "txnid",
    "txntype",
    "ts",
    "txndate",
    "custrefno",
    "umn",
    "payerseqnum",
    "mandateoperation",
    "validitystart",
    "validityend",
    "recurrencepattern",
    "umnexects",
    "revokable",
    "payeraddress",
    "payerbank",
    "payerpsp",
    "payerpsporgid",
    "payer_psp_bank",
    "remitter_bank",
    "remitterorgid",
    "remitteracctype",
    "payeeaddress",
    "payeename",
    "payeebank",
    "payee_psp_bank",
    "payeemcc",
    "payeetype",
    "payeemerchantgenre",
    "payeemerchanttype",
    "payeeonboardingtype",
    "payee_verified_name",
    "payeepsporgid",
    "beneficiary_bank",
    "txamount",
    "payeeamt",
    "purpose",
    "purposecode",
    "initiationmode",
    "initmode",
    "initiatedby",
    "initiatorpsp",
    "initiatorpsporgid",
    "cred_type",
    "cred_subtype",
    "cred_type_secondary",
    "cred_subtype_secondary",
    "pracctype",
    "prcode",
    "prorgid",
    "prdmobile",
    "pycode",
    "pyorgid",
    "pyrefaddr",
    "responsecode",
    "responseresult",
    "errorcode",
    "respcd",
    "result",
    "currstatusdesc",
    "txnnote",
    "asdt",
)

MCC_TO_PURPOSE_CODES: dict[str, tuple[str, ...]] = {
    "4899": ("06", "10"),
    "4814": ("06", "10"),
    "4900": ("10", "14"),
    "6300": ("07", "14"),
    "8062": ("05",),
    "8220": ("08",),
    "8211": ("08",),
    "6051": ("01", "02", "76"),
    "7372": ("14", "77"),
    "7841": ("14", "77"),
    "6513": ("14", "20"),
    "5964": ("77",),
    "5999": ("77", "09"),
    "7011": ("04",),
    "4511": ("03",),
    "5541": ("00",),
    "6011": ("12", "13"),
    "4121": ("00",),
    "4111": ("00",),
    "5411": ("00", "09"),
    "5812": ("00",),
    "5813": ("00",),
    "5912": ("00", "05"),
    "5311": ("09", "00"),
    "5732": ("00", "09"),
    "5691": ("09", "00"),
    "5261": ("00",),
    "8398": ("09",),
    "8011": ("05",),
    "4131": ("00",),
}
