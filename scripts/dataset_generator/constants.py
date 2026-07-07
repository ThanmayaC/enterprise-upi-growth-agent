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
    {"responsecode": "Z1", "responseresult": "FAILURE", "description": "Mandate reference invalid, expired, paused or revoked", "owner": "NPCI", "retryable": "N"},
    {"responsecode": "XL", "responseresult": "FAILURE", "description": "Daily transaction limit exceeded", "owner": "PayerPSP", "retryable": "N"},
    {"responsecode": "U55", "responseresult": "FAILURE", "description": "Transaction declined by customer", "owner": "Payer", "retryable": "N"},
)
SUCCESS_RESPONSE_CODE = "00"
FAILURE_RESPONSE_CODES: tuple[str, ...] = tuple(
    r["responsecode"] for r in RESPONSE_CODES if r["responseresult"] == "FAILURE"
)

# ---------------------------------------------------------------------------
# Error Code Master (populated only for failed transactions)
# ---------------------------------------------------------------------------
ERROR_CODES: tuple[dict, ...] = (
    {"errorcode": "U01", "description": "THE REQUEST IS DUPLICATE", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "LOW", "category": "Duplicate"},
    {"errorcode": "U02", "description": "AMOUNT CAP IS EXCEEDED", "type": "BD", "owner": "PayerPSP", "retryable": False, "severity": "LOW", "category": "Validation"},
    {"errorcode": "U03", "description": "NET DEBIT CAP IS EXCEEDED", "type": "BD", "owner": "PayerPSP", "retryable": False, "severity": "LOW", "category": "Validation"},
    {"errorcode": "U04", "description": "REQUEST IS NOT FOUND", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Validation"},
    {"errorcode": "U05", "description": "FORMATION IS NOT PROPER", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Validation"},
    {"errorcode": "U06", "description": "TRANSACTION ID IS MISMATCHED", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Validation"},
    {"errorcode": "U07", "description": "VALIDATION ERROR", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Validation"},
    {"errorcode": "U08", "description": "SYSTEM EXCEPTION", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "CRITICAL", "category": "System"},
    {"errorcode": "U09", "description": "REQAUTH TIME OUT FOR PAY", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Timeout"},
    {"errorcode": "U10", "description": "ILLEGAL OPERATION", "type": "BD", "owner": "PayerPSP", "retryable": False, "severity": "MEDIUM", "category": "Validation"},
    {"errorcode": "U11", "description": "CREDENTIALS IS NOT PRESENT", "type": "BD", "owner": "PayerPSP", "retryable": False, "severity": "MEDIUM", "category": "Validation"},
    {"errorcode": "U12", "description": "AMOUNT OR CURRENCY MISMATCH", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Validation"},
    {"errorcode": "U13", "description": "EXTERNAL ERROR", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "System"},
    {"errorcode": "U14", "description": "ENCRYPTION ERROR", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "System"},
    {"errorcode": "U15", "description": "CHECKSUM FAILED", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "System"},
    {"errorcode": "U16", "description": "RISK THRESHOLD EXCEEDED", "type": "BD", "owner": "PayerPSP", "retryable": False, "severity": "MEDIUM", "category": "Validation"},
    {"errorcode": "U17", "description": "PSP IS NOT REGISTERED", "type": "BD", "owner": "NPCI", "retryable": False, "severity": "MEDIUM", "category": "Validation"},
    {"errorcode": "U18", "description": "REQUEST AUTHORISATION ACKNOWLEDGEMENT IS NOT RECEIVED", "type": "TD", "owner": "PayerPSP", "retryable": True, "severity": "HIGH", "category": "Authentication"},
    {"errorcode": "U19", "description": "REQUEST AUTHORISATION IS DECLINED", "type": "BD", "owner": "PayerPSP", "retryable": False, "severity": "MEDIUM", "category": "Authentication"},
    {"errorcode": "U20", "description": "REQUEST AUTHORISATION TIMEOUT", "type": "TD", "owner": "PayerPSP", "retryable": True, "severity": "HIGH", "category": "Timeout"},
    {"errorcode": "U21", "description": "REQUEST AUTHORISATION IS NOT FOUND", "type": "TD", "owner": "PayerPSP", "retryable": True, "severity": "HIGH", "category": "Authentication"},
    {"errorcode": "U22", "description": "CM REQUEST IS DECLINED", "type": "TD", "owner": "PayerPSP", "retryable": True, "severity": "HIGH", "category": "Authentication"},
    {"errorcode": "U23", "description": "CM REQUEST TIMEOUT", "type": "TD", "owner": "PayerPSP", "retryable": True, "severity": "HIGH", "category": "Timeout"},
    {"errorcode": "U24", "description": "CM REQUEST ACKNOWLEDGEMENT IS NOT RECEIVED", "type": "TD", "owner": "PayerPSP", "retryable": True, "severity": "HIGH", "category": "Authentication"},
    {"errorcode": "U25", "description": "CM URL IS NOT FOUND", "type": "TD", "owner": "PayerPSP", "retryable": True, "severity": "HIGH", "category": "Authentication"},
    {"errorcode": "U26", "description": "PSP REQUEST CREDIT PAY ACKNOWLEDGEMENT IS NOT RECEIVED", "type": "TD", "owner": "PayerPSP", "retryable": True, "severity": "HIGH", "category": "Authentication"},
    {"errorcode": "U27", "description": "NO RESPONSE FROM PSP", "type": "TD", "owner": "PayerPSP", "retryable": True, "severity": "HIGH", "category": "PSP"},
    {"errorcode": "U28", "description": "REMITTER BANK NOT AVAILABLE", "type": "TD", "owner": "IssuerBank", "retryable": True, "severity": "HIGH", "category": "Issuer Bank"},
    {"errorcode": "U29", "description": "ADDRESS RESOLUTION IS FAILED", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "System"},
    {"errorcode": "U30", "description": "DEBIT HAS BEEN FAILED", "type": "TD", "owner": "IssuerBank", "retryable": True, "severity": "HIGH", "category": "Settlement"},
    {"errorcode": "U31", "description": "CREDIT HAS BEEN FAILED", "type": "TD", "owner": "BeneficiaryBank", "retryable": True, "severity": "HIGH", "category": "Beneficiary Bank"},
    {"errorcode": "U32", "description": "CREDIT REVERT HAS BEEN FAILED", "type": "TD", "owner": "BeneficiaryBank", "retryable": True, "severity": "HIGH", "category": "Beneficiary Bank"},
    {"errorcode": "U33", "description": "DEBIT REVERT HAS BEEN FAILED", "type": "TD", "owner": "IssuerBank", "retryable": True, "severity": "HIGH", "category": "Settlement"},
    {"errorcode": "U34", "description": "REVERTED", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Settlement"},
    {"errorcode": "U35", "description": "RESPONSE IS ALREADY BEEN RECEIVED", "type": "TD", "owner": "NPCI", "retryable": False, "severity": "LOW", "category": "System"},
    {"errorcode": "U36", "description": "REQUEST IS ALREADY BEEN SENT", "type": "TD", "owner": "NPCI", "retryable": False, "severity": "LOW", "category": "System"},
    {"errorcode": "U37", "description": "REVERSAL HAS BEEN SENT", "type": "TD", "owner": "NPCI", "retryable": False, "severity": "LOW", "category": "System"},
    {"errorcode": "U38", "description": "RESPONSE IS ALREADY BEEN SENT", "type": "TD", "owner": "NPCI", "retryable": False, "severity": "LOW", "category": "System"},
    {"errorcode": "U39", "description": "TRANSACTION IS ALREADY BEEN FAILED", "type": "TD", "owner": "NPCI", "retryable": False, "severity": "LOW", "category": "System"},
    {"errorcode": "U40", "description": "IMPS PROCESSING FAILED IN UPI", "type": "TD", "owner": "IMPS", "retryable": True, "severity": "HIGH", "category": "IMPS"},
    {"errorcode": "U41", "description": "IMPS IS SIGNED OFF", "type": "TD", "owner": "IMPS", "retryable": True, "severity": "HIGH", "category": "IMPS"},
    {"errorcode": "U42", "description": "IMPS TRANSACTION IS ALREADY BEEN PROCESSED", "type": "TD", "owner": "IMPS", "retryable": False, "severity": "HIGH", "category": "IMPS"},
    {"errorcode": "U43", "description": "IMPS IS DECLINED", "type": "TD", "owner": "IMPS", "retryable": True, "severity": "HIGH", "category": "IMPS"},
    {"errorcode": "U44", "description": "FORM HAS BEEN SIGNED OFF", "type": "TD", "owner": "IMPS", "retryable": True, "severity": "HIGH", "category": "IMPS"},
    {"errorcode": "U45", "description": "FORM PROCESSING HAS BEEN FAILED IN UPI", "type": "TD", "owner": "IMPS", "retryable": True, "severity": "HIGH", "category": "IMPS"},
    {"errorcode": "U46", "description": "REQUEST CREDIT IS NOT FOUND", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Validation"},
    {"errorcode": "U47", "description": "REQUEST DEBIT IS NOT FOUND", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Validation"},
    {"errorcode": "U48", "description": "TRANSACTION ID IS NOT PRESENT", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Validation"},
    {"errorcode": "U49", "description": "REQUEST MESSAGE ID IS NOT PRESENT", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Validation"},
    {"errorcode": "U50", "description": "IFSC IS NOT PRESENT", "type": "BD", "owner": "PayeePSP", "retryable": False, "severity": "MEDIUM", "category": "Validation"},
    {"errorcode": "U51", "description": "REQUEST REFUND IS NOT FOUND", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Validation"},
    {"errorcode": "U52", "description": "PSP ORGID NOT FOUND", "type": "BD", "owner": "NPCI", "retryable": False, "severity": "MEDIUM", "category": "Validation"},
    {"errorcode": "U53", "description": "PSP REQUEST PAY DEBIT ACKNOWLEDGEMENT NOT RECEIVED", "type": "TD", "owner": "PayerPSP", "retryable": True, "severity": "HIGH", "category": "PSP"},
    {"errorcode": "U54", "description": "TRANSACTION ID OR AMOUNT IN CREDENTIAL BLOCK DOES NOT MATCH WITH THAT IN REQPAY", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Validation"},
    {"errorcode": "U55", "description": "MESSAGE INTEGRITY FAILED DUE TO ORGID MISMATCH", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Validation"},
    {"errorcode": "U56", "description": "NUMBER OF PAYEES DIFFERS FROM ORIGINAL REQUEST", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Validation"},
    {"errorcode": "U57", "description": "PAYEE AMOUNT DIFFERS FROM ORIGINAL REQUEST", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Validation"},
    {"errorcode": "U58", "description": "PAYER AMOUNT DIFFERS FROM ORIGINAL REQUEST", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Validation"},
    {"errorcode": "U59", "description": "PAYEE ADDRESS DIFFERS FROM ORIGINAL REQUEST", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Validation"},
    {"errorcode": "U60", "description": "PAYER ADDRESS DIFFERS FROM ORIGINAL REQUEST", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Validation"},
    {"errorcode": "U61", "description": "PAYEE INFO DIFFERS FROM ORIGINAL REQUEST", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Validation"},
    {"errorcode": "U62", "description": "PAYER INFO DIFFERS FROM ORIGINAL REQUEST", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Validation"},
    {"errorcode": "U63", "description": "DEVICE REGISTRATION FAILED IN UPI", "type": "TD", "owner": "PayerPSP", "retryable": True, "severity": "HIGH", "category": "Authentication"},
    {"errorcode": "U64", "description": "DATA TAG SHOULD CONTAIN 4 PARTS DURING DEVICE REGISTRATION", "type": "TD", "owner": "PayerPSP", "retryable": True, "severity": "HIGH", "category": "Authentication"},
    {"errorcode": "U65", "description": "CREDS BLOCK SHOULD CONTAIN CORRECT ELEMENTS DURING DEVICE REGISTRATION", "type": "TD", "owner": "PayerPSP", "retryable": True, "severity": "HIGH", "category": "Authentication"},
    {"errorcode": "U66", "description": "DEVICE FINGERPRINT MISMATCH", "type": "BD", "owner": "PayerPSP", "retryable": False, "severity": "MEDIUM", "category": "Authentication"},
    {"errorcode": "U67", "description": "DEBIT TIMEOUT", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Timeout"},
    {"errorcode": "U68", "description": "CREDIT TIMEOUT", "type": "TD", "owner": "BeneficiaryBank", "retryable": True, "severity": "HIGH", "category": "Timeout"},
    {"errorcode": "U69", "description": "COLLECT EXPIRED", "type": "BD", "owner": "NPCI", "retryable": False, "severity": "LOW", "category": "Validation"},
    {"errorcode": "U70", "description": "RECEIVED LATE RESPONSE", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Timeout"},
    {"errorcode": "U71", "description": "MERCHANT CREDIT NOT SUPPORTED IN IMPS", "type": "TD", "owner": "IMPS", "retryable": True, "severity": "HIGH", "category": "IMPS"},
    {"errorcode": "U72", "description": "VAE FAILED", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "System"},
    {"errorcode": "U74", "description": "PAYER ACCOUNT MISMATCH", "type": "TD", "owner": "IssuerBank", "retryable": True, "severity": "HIGH", "category": "Validation"},
    {"errorcode": "U75", "description": "PAYEE ACCOUNT MISMATCH", "type": "TD", "owner": "BeneficiaryBank", "retryable": True, "severity": "HIGH", "category": "Beneficiary Bank"},
    {"errorcode": "U76", "description": "MOBILE BANKING REGISTRATION FORMAT NOT SUPPORTED BY THE ISSUER BANK", "type": "TD", "owner": "IssuerBank", "retryable": True, "severity": "HIGH", "category": "Validation"},
    {"errorcode": "U77", "description": "MERCHANT BLOCKED", "type": "TD", "owner": "Merchant", "retryable": True, "severity": "HIGH", "category": "Merchant"},
    {"errorcode": "U78", "description": "BENEFICIARY BANK OFFLINE", "type": "TD", "owner": "BeneficiaryBank", "retryable": True, "severity": "HIGH", "category": "Beneficiary Bank"},
    {"errorcode": "U80", "description": "PAYER PSP THROTTLE DECLINE", "type": "TD", "owner": "PayerPSP", "retryable": True, "severity": "HIGH", "category": "PSP"},
    {"errorcode": "U81", "description": "REMITTER BANK DEEMED CHECK DECLINE", "type": "TD", "owner": "IssuerBank", "retryable": True, "severity": "HIGH", "category": "Issuer Bank"},
    {"errorcode": "U82", "description": "READ TIMEOUT IN REQPAY CREDIT", "type": "TD", "owner": "BeneficiaryBank", "retryable": True, "severity": "HIGH", "category": "Timeout"},
    {"errorcode": "U84", "description": "BENEFICIARY BANK DEEMED CHECK DECLINE", "type": "TD", "owner": "BeneficiaryBank", "retryable": True, "severity": "HIGH", "category": "Beneficiary Bank"},
    {"errorcode": "U85", "description": "CONNECTION TIMEOUT IN REQPAY DEBIT", "type": "TD", "owner": "IssuerBank", "retryable": True, "severity": "HIGH", "category": "Timeout"},
    {"errorcode": "U86", "description": "REMITTER BANK THROTTLING DECLINE", "type": "TD", "owner": "IssuerBank", "retryable": True, "severity": "HIGH", "category": "Issuer Bank"},
    {"errorcode": "U87", "description": "READ TIMEOUT IN REQPAY DEBIT", "type": "TD", "owner": "IssuerBank", "retryable": True, "severity": "HIGH", "category": "Timeout"},
    {"errorcode": "U88", "description": "CONNECTION TIMEOUT IN REQPAY CREDIT", "type": "TD", "owner": "BeneficiaryBank", "retryable": True, "severity": "HIGH", "category": "Timeout"},
    {"errorcode": "U89", "description": "BENEFICIARY BANK THROTTLING DECLINE", "type": "TD", "owner": "BeneficiaryBank", "retryable": True, "severity": "HIGH", "category": "Beneficiary Bank"},
    {"errorcode": "U90", "description": "REMITTER BANK DEEMED HIGH RESPONSE TIME CHECK DECLINE", "type": "TD", "owner": "IssuerBank", "retryable": True, "severity": "HIGH", "category": "Issuer Bank"},
    {"errorcode": "U91", "description": "BENEFICIARY BANK DEEMED HIGH RESPONSE TIME CHECK DECLINE", "type": "TD", "owner": "BeneficiaryBank", "retryable": True, "severity": "HIGH", "category": "Beneficiary Bank"},
    {"errorcode": "U92", "description": "PAYER PSP NOT AVAILABLE", "type": "TD", "owner": "PayerPSP", "retryable": True, "severity": "HIGH", "category": "PSP"},
    {"errorcode": "U93", "description": "PAYEE PSP NOT AVAILABLE", "type": "TD", "owner": "PayeePSP", "retryable": True, "severity": "HIGH", "category": "PSP"},
    {"errorcode": "U94", "description": "PAYEE PSP THROTTLE DECLINE", "type": "TD", "owner": "PayeePSP", "retryable": True, "severity": "HIGH", "category": "PSP"},
    {"errorcode": "U95", "description": "PAYEE VPA AADHAAR OR IIN VPA IS DISABLED", "type": "BD", "owner": "NPCI", "retryable": False, "severity": "MEDIUM", "category": "Validation"},
    {"errorcode": "U96", "description": "PAYER AND PAYEE IFSC/ACNUM CAN'T BE SAME", "type": "BD", "owner": "NPCI", "retryable": False, "severity": "MEDIUM", "category": "Validation"},
    {"errorcode": "U97", "description": "PSP REQUEST META ACKNOWLEDGEMENT NOT RECEIVED", "type": "TD", "owner": "PayerPSP", "retryable": True, "severity": "HIGH", "category": "PSP"},
    {"errorcode": "U98", "description": "NULL ACK RECEIVED BY UPI FOR META TRANSACTION", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "System"},
    {"errorcode": "U99", "description": "NEGATIVE ACK RECEIVED BY UPI FOR META TRANSACTION", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "System"},
    {"errorcode": "UA1", "description": "HEADER & URL VERSION IS MISMATCHED", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Version"},
    {"errorcode": "UA2", "description": "VERSION/TAGS SENT NOT SUPPORTED BY PSP/BANK", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Version"},
    {"errorcode": "UA3", "description": "PAYER/PAYEE PSP, HEADER OR URL VERSION MISMATCHED", "type": "TD", "owner": "PayerPSP", "retryable": True, "severity": "HIGH", "category": "Version"},
    {"errorcode": "UA4", "description": "PAYER/PAYEE PSP, REQUEST & RESPONSE HEADER VERSION MISMATCH", "type": "TD", "owner": "PayerPSP", "retryable": True, "severity": "HIGH", "category": "Version"},
    {"errorcode": "UA5", "description": "PAYER/PAYEE PSP, VERSION/TAGS NOT SUPPORTED BY PSP/BANK", "type": "TD", "owner": "PayerPSP", "retryable": True, "severity": "HIGH", "category": "Version"},
    {"errorcode": "UA6", "description": "URL VERSION MISMATCHED (NEG ACK FOR RESPAUTH. ERROR CODE U18 IN FINAL RESPPAY.)", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Version"},
    {"errorcode": "UA7", "description": "REMITTER BANK, REQUEST & RESPONSE HEADER VERSION MISMATCH", "type": "TD", "owner": "IssuerBank", "retryable": True, "severity": "HIGH", "category": "Version"},
    {"errorcode": "UA8", "description": "REMITTER BANK, HEADER OR URL VERSION MISMATCHED", "type": "TD", "owner": "IssuerBank", "retryable": True, "severity": "HIGH", "category": "Version"},
    {"errorcode": "UA9", "description": "REMITTER BANK, VERSION/TAGS SENT NOT SUPPORTED BY BANK", "type": "TD", "owner": "IssuerBank", "retryable": True, "severity": "HIGH", "category": "Version"},
    {"errorcode": "UB1", "description": "BENEFICIARY BANK, REQUEST & RESPONSE HEADER VERSION MISMATCH", "type": "TD", "owner": "BeneficiaryBank", "retryable": True, "severity": "HIGH", "category": "Version"},
    {"errorcode": "UB2", "description": "BENEFICIARY BANK, HEADER OR URL VERSION MISMATCHED", "type": "TD", "owner": "BeneficiaryBank", "retryable": True, "severity": "HIGH", "category": "Version"},
    {"errorcode": "UB3", "description": "BENEFICIARY BANK, VERSION/TAGS SENT NOT SUPPORTED BY BANK", "type": "TD", "owner": "BeneficiaryBank", "retryable": True, "severity": "HIGH", "category": "Version"},
    {"errorcode": "UB7", "description": "OTHER BANK/PSP IS NOT SUPPORTED IN 2.0 VERSION", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Version"},
    {"errorcode": "UB8", "description": "PAYER PSP DOES NOT SUPPORTS VERSION", "type": "TD", "owner": "PayerPSP", "retryable": True, "severity": "HIGH", "category": "Version"},
    {"errorcode": "UB9", "description": "REMITTER BANK DOES NOT SUPPORT VERSION", "type": "TD", "owner": "IssuerBank", "retryable": True, "severity": "HIGH", "category": "Version"},
    {"errorcode": "UC2", "description": "BENEFICIARY BANK DOES NOT SUPPORT VERSION", "type": "TD", "owner": "BeneficiaryBank", "retryable": True, "severity": "HIGH", "category": "Version"},
    {"errorcode": "UM0", "description": "MANDATE NOT FOUND", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Mandate"},
    {"errorcode": "UM1", "description": "MANDATE ALREADY EXECUTED", "type": "BD", "owner": "NPCI", "retryable": False, "severity": "MEDIUM", "category": "Mandate"},
    {"errorcode": "UM2", "description": "MANDATE EXPIRED", "type": "BD", "owner": "NPCI", "retryable": False, "severity": "LOW", "category": "Mandate"},
    {"errorcode": "UM3", "description": "MANDATE REVOKED", "type": "BD", "owner": "NPCI", "retryable": False, "severity": "LOW", "category": "Mandate"},
    {"errorcode": "UM4", "description": "MANDATE PAUSED", "type": "BD", "owner": "NPCI", "retryable": False, "severity": "LOW", "category": "Mandate"},
    {"errorcode": "UM5", "description": "MANDATE EXECUTION NOT ALLOWED", "type": "BD", "owner": "NPCI", "retryable": False, "severity": "MEDIUM", "category": "Mandate"},
    {"errorcode": "UM6", "description": "INVALID MANDATE DETAILS", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Mandate"},
    {"errorcode": "UM7", "description": "MANDATE ALREADY EXISTS", "type": "BD", "owner": "NPCI", "retryable": False, "severity": "MEDIUM", "category": "Mandate"},
    {"errorcode": "UM8", "description": "MANDATE REGISTRATION FAILED", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "Mandate"},
    {"errorcode": "UM9", "description": "MANDATE MODIFICATION NOT ALLOWED", "type": "BD", "owner": "NPCI", "retryable": False, "severity": "MEDIUM", "category": "Mandate"},
    {"errorcode": "UN0", "description": "MANDATE EXECUTION WINDOW EXPIRED", "type": "BD", "owner": "NPCI", "retryable": False, "severity": "LOW", "category": "AutoPay"},
    {"errorcode": "UN1", "description": "PRE-DEBIT NOTIFICATION NOT SENT", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "AutoPay"},
    {"errorcode": "UN2", "description": "PRE-DEBIT NOTIFICATION ACKNOWLEDGEMENT NOT RECEIVED", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "AutoPay"},
    {"errorcode": "UN3", "description": "PRE-DEBIT NOTIFICATION DECLINED", "type": "BD", "owner": "NPCI", "retryable": False, "severity": "MEDIUM", "category": "AutoPay"},
    {"errorcode": "UN4", "description": "PRE-DEBIT NOTIFICATION TIMEOUT", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "AutoPay"},
    {"errorcode": "UN5", "description": "MANDATE STATUS INVALID", "type": "BD", "owner": "NPCI", "retryable": False, "severity": "MEDIUM", "category": "AutoPay"},
    {"errorcode": "UN6", "description": "MANDATE FREQUENCY MISMATCH", "type": "BD", "owner": "NPCI", "retryable": False, "severity": "MEDIUM", "category": "AutoPay"},
    {"errorcode": "UN7", "description": "EXECUTION DATE NOT VALID", "type": "BD", "owner": "NPCI", "retryable": False, "severity": "MEDIUM", "category": "AutoPay"},
    {"errorcode": "UN8", "description": "MAXIMUM EXECUTION COUNT EXCEEDED", "type": "BD", "owner": "NPCI", "retryable": False, "severity": "MEDIUM", "category": "AutoPay"},
    {"errorcode": "UN9", "description": "MANDATE AMOUNT LIMIT EXCEEDED", "type": "BD", "owner": "NPCI", "retryable": False, "severity": "MEDIUM", "category": "AutoPay"},
    {"errorcode": "UP0", "description": "PAYER DOES NOT SUPPORT AUTOPAY", "type": "BD", "owner": "PayerPSP", "retryable": False, "severity": "LOW", "category": "AutoPay"},
    {"errorcode": "UP1", "description": "PAYEE DOES NOT SUPPORT AUTOPAY", "type": "BD", "owner": "PayeePSP", "retryable": False, "severity": "LOW", "category": "AutoPay"},
    {"errorcode": "UP2", "description": "AUTOPAY VERSION NOT SUPPORTED", "type": "TD", "owner": "NPCI", "retryable": True, "severity": "HIGH", "category": "AutoPay"},
    {"errorcode": "S99", "description": "GRACEFUL DECLINE", "type": "BD", "owner": "NPCI", "retryable": False, "severity": "MEDIUM", "category": "System"},
    {"errorcode": "HS1", "description": "HSM IS OFFLINE", "type": "TD", "owner": "HSM", "retryable": True, "severity": "CRITICAL", "category": "HSM"},
    {"errorcode": "HS2", "description": "HSM TIME OUT", "type": "TD", "owner": "HSM", "retryable": True, "severity": "CRITICAL", "category": "HSM"},
    {"errorcode": "HS3", "description": "HSM COMMUNICATION ERROR", "type": "TD", "owner": "HSM", "retryable": True, "severity": "CRITICAL", "category": "HSM"},
)

RESPONSE_TO_ERROR_MAP: dict[str, tuple[str, ...]] = {
    "U69": ("U27",),          # Transaction failed at Payer PSP -> NO RESPONSE FROM PSP
    "U30": ("U05",),          # Format error at Issuer -> FORMATION IS NOT PROPER
    "U16": ("U19",),          # Insufficient funds -> REQUEST AUTHORISATION IS DECLINED
    "U17": ("U11",),          # Invalid MPIN -> CREDENTIALS IS NOT PRESENT
    "U67": ("U78",),          # Beneficiary bank unavailable -> BENEFICIARY BANK OFFLINE
    "U68": ("U93",),          # Payee PSP timeout -> PAYEE PSP NOT AVAILABLE
    "Z9": ("U08",),           # NPCI switch timeout -> SYSTEM EXCEPTION
    "U90": ("U28",),          # Remitter bank system unavailable -> REMITTER BANK NOT AVAILABLE
    "U53": ("U01",),          # Duplicate transaction -> THE REQUEST IS DUPLICATE
    "U54": ("U30",),          # Debit failed, credit not attempted -> DEBIT HAS BEEN FAILED
    "Z1": ("UM0", "UM2", "UM3", "UM4"),  # Mandate invalid/expired/paused/revoked
    "XL": ("U03",),           # Daily transaction limit exceeded -> NET DEBIT CAP IS EXCEEDED
    "U55": ("U19",),          # Transaction declined by customer -> REQUEST AUTHORISATION IS DECLINED
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
# renamed, added to, or removed from without a deliberate schema-review
# pass. Sourced verbatim from SDS.pdf, with Task 6's cleanup applied:
# initmode, respcd, result, beneficiary_bank, and remitter_bank were
# removed because they were empirically verified (100% match across a
# full generated batch) to carry EXACTLY the same value as
# initiationmode, responsecode, responseresult, payeebank, and payerbank
# respectively — true duplicates, not independently meaningful columns.
# Columns that only *coincidentally* matched in this synthetic run but
# represent a genuinely distinct real-world concept (e.g. payeeamt vs
# txamount, which the original spec explicitly allows to diverge when
# fees apply; prorgid/pyorgid/pracctype/pyrefaddr, which are Product-
# domain fields distinct from the Payer-domain fields they currently
# mirror; asdt vs ts, which distinguishes event time from an as-of/
# settlement time) were deliberately KEPT per "do not remove information
# required for enterprise analytics."
# ---------------------------------------------------------------------------
FACT_TABLE_FIELDS: tuple[str, ...] = (
    "transaction_type",
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
    "txamount",
    "payeeamt",
    "purpose",
    "purposecode",
    "initiationmode",
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

# ===========================================================================
# BUSINESS-EVENT DATA MODEL
#
# The fact table represents ONE ROW PER BUSINESS EVENT (not one row per API
# call). "transaction_type" carries the business event type below. The
# original API/lifecycle constants above are retained only in case a
# separate, optional api_event_generator.py is built later (per the SDS
# note); they are NOT used by transaction_generator.py.
# ===========================================================================

# ---------------------------------------------------------------------------
# Business event types (values of the "transaction_type" column)
# ---------------------------------------------------------------------------
BUSINESS_EVENT_TYPES: tuple[str, ...] = (
    "P2P_PAYMENT",
    "MERCHANT_PAYMENT",
    "MERCHANT_REFUND",
    "MANDATE_REGISTRATION",
    "MANDATE_UPDATE",
    "MANDATE_PAUSE",
    "MANDATE_RESUME",
    "MANDATE_REVOKE",
    "PDN",
    "AUTOPAY_EXECUTION",
    "AUTOPAY_RETRY",
    "BALANCE_CHECK",
    "COLLECT_REQUEST",
    "COLLECT_PAYMENT",
    "QR_PAYMENT",
    "INTENT_PAYMENT",
    "BBPS_PAYMENT",
    "INTERNATIONAL_PAYMENT",
)

# Events that move money (financial) vs. administrative/status-only events.
FINANCIAL_EVENT_TYPES: frozenset[str] = frozenset({
    "P2P_PAYMENT", "MERCHANT_PAYMENT", "MERCHANT_REFUND", "AUTOPAY_EXECUTION",
    "AUTOPAY_RETRY", "COLLECT_PAYMENT", "QR_PAYMENT", "INTENT_PAYMENT",
    "BBPS_PAYMENT", "INTERNATIONAL_PAYMENT",
})
NON_FINANCIAL_EVENT_TYPES: frozenset[str] = frozenset(BUSINESS_EVENT_TYPES) - FINANCIAL_EVENT_TYPES

# Events that carry/require an active mandate (UMN) context.
MANDATE_RELATED_EVENT_TYPES: frozenset[str] = frozenset({
    "MANDATE_REGISTRATION", "MANDATE_UPDATE", "MANDATE_PAUSE", "MANDATE_RESUME",
    "MANDATE_REVOKE", "PDN", "AUTOPAY_EXECUTION", "AUTOPAY_RETRY",
})

# Default top-level transaction-mix percentages (config-overridable).
# Sums to 100. PDN rows are generated alongside AutoPay Executions and are
# not counted separately in this top-level mix.
DEFAULT_BUSINESS_EVENT_DISTRIBUTION: dict[str, float] = {
    "MERCHANT_PAYMENT": 40.0,
    "P2P_PAYMENT": 30.0,
    "QR_PAYMENT": 10.0,
    "COLLECT_PAYMENT": 5.0,
    "BBPS_PAYMENT": 5.0,
    "AUTOPAY_EXECUTION": 5.0,
    "MANDATE_REGISTRATION": 2.0,
    "MANDATE_UPDATE": 1.0,
    "MANDATE_PAUSE_RESUME_REVOKE": 1.0,
    "MERCHANT_REFUND": 1.0,
}

# ---------------------------------------------------------------------------
# Transaction status (repurposes "responseresult" / "result")
# ---------------------------------------------------------------------------
TRANSACTION_STATUSES: tuple[str, ...] = (
    "SUCCESS", "FAILURE",
)
# These strictly mirror RESPONSE_CODES[*]["responseresult"], which only
# ever takes these two values. Finer-grained detail (why a transaction
# failed, whether it is retryable) lives in failure_reason / the
# retryable flag on the response code itself — NOT in extra invented
# status labels like TIMEOUT/DECLINED/RETRY/PENDING, which never appear
# in the official Response Code Master.
TERMINAL_SUCCESS_STATUSES: frozenset[str] = frozenset({"SUCCESS"})
TERMINAL_FAILURE_STATUSES: frozenset[str] = frozenset({"FAILURE"})

# ---------------------------------------------------------------------------
# Failure reasons -> (owner, retryable, mapped responsecode, mapped errorcode)
# Codes must exist in RESPONSE_CODES / ERROR_CODES above.
# ---------------------------------------------------------------------------
FAILURE_REASONS: dict[str, dict] = {
    # INSUFFICIENT_BALANCE and CUSTOMER_DECLINED both surface at the UPI
    # protocol layer as "the bank/customer declined the authorisation"
    # (U19) — the official NPCI U-series is protocol/messaging-layer
    # error codes, not core-banking decline reasons, so a real switch
    # would not distinguish "insufficient funds" from "customer declined"
    # any further than this without seeing the bank's own core-banking
    # response, exactly like production UPI switches behave.
    "INSUFFICIENT_BALANCE": {"owner": "PayerPSP", "retryable": False, "responsecode": "U16", "errorcode": "U19"},
    "BANK_DOWN": {"owner": "IssuerBank", "retryable": True, "responsecode": "U90", "errorcode": "U28"},
    "PSP_TIMEOUT": {"owner": "PayeePSP", "retryable": True, "responsecode": "U68", "errorcode": "U27"},
    "CUSTOMER_DECLINED": {"owner": "Payer", "retryable": False, "responsecode": "U55", "errorcode": "U19"},
    "MANDATE_EXPIRED": {"owner": "NPCI", "retryable": False, "responsecode": "Z1", "errorcode": "UM2"},
    "MANDATE_PAUSED": {"owner": "NPCI", "retryable": False, "responsecode": "Z1", "errorcode": "UM4"},
    "MANDATE_REVOKED": {"owner": "NPCI", "retryable": False, "responsecode": "Z1", "errorcode": "UM3"},
    "DAILY_LIMIT_EXCEEDED": {"owner": "PayerPSP", "retryable": False, "responsecode": "XL", "errorcode": "U03"},
    "TECHNICAL_ERROR": {"owner": "NPCI", "retryable": True, "responsecode": "Z9", "errorcode": "U08"},
    # New reasons (Task: add PRE_DEBIT_FAILURE and AUTOPAY_NOT_SUPPORTED),
    # both reuse the existing mandate-cluster "Z1" response code since no
    # new response code is being introduced (schema/response-code master
    # left untouched per the task's constraints).
    "PRE_DEBIT_FAILURE": {"owner": "NPCI", "retryable": True, "responsecode": "Z1", "errorcode": "UN1"},
    "AUTOPAY_NOT_SUPPORTED": {"owner": "PayerPSP", "retryable": False, "responsecode": "Z1", "errorcode": "UP0"},
}
RETRYABLE_FAILURE_REASONS: tuple[str, ...] = tuple(
    reason for reason, meta in FAILURE_REASONS.items() if meta["retryable"]
)
NON_RETRYABLE_FAILURE_REASONS: tuple[str, ...] = tuple(
    reason for reason, meta in FAILURE_REASONS.items() if not meta["retryable"]
)

# ---------------------------------------------------------------------------
# Mandate lifecycle states
# ---------------------------------------------------------------------------
MANDATE_STATES: tuple[str, ...] = (
    "ACTIVE", "PAUSED", "REVOKED", "EXPIRED", "FAILED", "UPDATED", "SUSPENDED",
)
# States from which a mandate may still be executed (PDN + AutoPay attempted).
EXECUTABLE_MANDATE_STATES: frozenset[str] = frozenset({"ACTIVE", "UPDATED"})
# Legal state transitions: from_state -> allowed next states.
MANDATE_STATE_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "ACTIVE": ("PAUSED", "REVOKED", "EXPIRED", "UPDATED", "SUSPENDED", "FAILED"),
    "UPDATED": ("PAUSED", "REVOKED", "EXPIRED", "SUSPENDED", "ACTIVE"),
    "PAUSED": ("ACTIVE", "REVOKED", "EXPIRED"),
    "SUSPENDED": ("ACTIVE", "REVOKED", "EXPIRED"),
    "REVOKED": (),
    "EXPIRED": (),
    "FAILED": (),
}

# ---------------------------------------------------------------------------
# Customer personas — behavioural archetypes (used by persona_simulator.py)
# ---------------------------------------------------------------------------
CUSTOMER_PERSONAS: tuple[str, ...] = (
    "SALARY_EMPLOYEE", "COLLEGE_STUDENT", "BUSINESS_OWNER",
    "RETIRED", "FAMILY", "FREELANCER",
)

# ---------------------------------------------------------------------------
# Merchant behaviour archetypes (used by merchant_behavior.py), keyed by MCC.
# Determines which business events a merchant of that category mostly drives.
# ---------------------------------------------------------------------------
MCC_BEHAVIOR_PROFILE: dict[str, str] = {
    "7841": "AUTOPAY_HEAVY",       # OTT/Streaming (Netflix-like)
    "7372": "AUTOPAY_HEAVY",       # SaaS
    "4900": "BBPS_AUTOPAY",        # Electricity/Utilities
    "4899": "BBPS_AUTOPAY",        # Cable/DTH
    "4814": "RECHARGE_AUTOPAY",    # Telecom
    "6300": "LARGE_MONTHLY_AUTOPAY",  # Insurance
    "8220": "SEASONAL_LARGE",      # Colleges
    "8211": "SEASONAL_LARGE",      # Schools
    "8062": "HIGH_VALUE",          # Hospitals
    "4511": "HIGH_VALUE",          # Airlines
    "5964": "MERCHANT_HEAVY",      # E-commerce (Amazon-like)
    "5812": "MERCHANT_HEAVY",      # Restaurants/food delivery (Swiggy-like)
    "5411": "MERCHANT_HEAVY",      # Grocery
}
DEFAULT_MERCHANT_BEHAVIOR: str = "MERCHANT_HEAVY"

