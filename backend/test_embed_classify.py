from classifiers.heuristics import classify_single_text

examples = [
    ("Form W-2 Wage and Tax Statement\nEmployer identification number ...", "W2"),
    ("Year-to-date earnings\nGross pay\nNet pay\nPay Period 07/2025", "Paystub"),
    ("Statement Period: 01/01/2025 - 01/31/2025\nEnding Balance: $1,234.56", "BankStatement"),
    ("Driver License\nDOB: 01/01/1980\nID Number: XYZ", "ID")
]

for txt, expected in examples:
    label, score, reasons, snippet = classify_single_text(txt)
    print(f"EXPECTED={expected} => PREDICTED={label} ({score}) reasons={reasons}")
