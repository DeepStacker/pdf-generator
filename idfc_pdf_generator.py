import os
import argparse
import pdf_logic as logic

def process_excel_cli(input_excel, output_dir, audit_type):
    audit_type = str(audit_type).strip().upper()
    os.makedirs(output_dir, exist_ok=True)

    print(f"Reading Excel: {input_excel}")
    print(f"Audit Type: {audit_type}")

    sheet_name, headers, all_rows = logic.read_excel(input_excel)

    groups = {}
    for row in all_rows:
        branch = str(row.get("CurrentBranch", "UNKNOWN")).strip()
        groups.setdefault(branch if branch not in ("None", "") else "UNKNOWN", []).append(row)

    total = 0
    for branch_code, branch_rows in sorted(groups.items()):
        try:
            branch_name = str(branch_rows[0].get("CurrentBranchName", "")).strip()
            state = str(branch_rows[0].get("State", "")).strip()
            safe_branch_name = (branch_name.replace("/", "_").replace("\\", "_") if branch_name else str(branch_code))

            output_file = os.path.join(output_dir, f"{safe_branch_name}_{audit_type}.pdf")
            print(f"Generating -> {output_file}")

            logic.generate_pdf(audit_type, branch_code, branch_name, state, branch_rows, output_file)
            total += 1

        except Exception as e:
            print(f"Error generating PDF for branch {branch_code}: {e}")

    print(f"\nDone. Generated {total} PDFs.")
    print(f"Output Folder: {output_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate branch-wise PDFs from Excel")
    parser.add_argument("input_file", help="Path to Excel file")
    parser.add_argument("-t", "--type", default="POA", help="Pass POA or TAF")
    parser.add_argument("-o", "--output-dir", default="generated_pdfs", help="Output folder")
    args = parser.parse_args()

    try:
        process_excel_cli(args.input_file, args.output_dir, args.type)
    except Exception as e:
        print(f"Fatal Error: {e}")