import os
import pandas as pd
import pymupdf

def create_procurement_documents(target_dir: str):
    os.makedirs(target_dir, exist_ok=True)

    # 1. spare_parts_catalog.csv
    parts_data = [
        {
            "part_number": "NV-PUMP-001",
            "description": "Main Engine Fuel Oil Delivery Pump",
            "equipment_system": "Main Propulsion Fuel System",
            "primary_supplier": "Nordik Marine Spares",
            "unit_price_usd": 4250.00,
            "warehouse_location": "Rotterdam",
            "stock_on_hand": 4,
            "min_safety_stock": 2,
            "lead_time_days": 12
        },
        {
            "part_number": "TB-BRG-882",
            "description": "Turbocharger High-Speed Bearing Assembly",
            "equipment_system": "Exhaust Gas Turbocharger",
            "primary_supplier": "Nordik Marine Spares",
            "unit_price_usd": 3100.00,
            "warehouse_location": "Singapore",
            "stock_on_hand": 2,
            "min_safety_stock": 1,
            "lead_time_days": 5
        },
        {
            "part_number": "CYL-LINER-72",
            "description": "2-Stroke Diesel Cylinder Liner 720mm",
            "equipment_system": "Main Propulsion Engine Block",
            "primary_supplier": "Oceanic Engineering Ltd",
            "unit_price_usd": 1800.00,
            "warehouse_location": "Busan",
            "stock_on_hand": 8,
            "min_safety_stock": 4,
            "lead_time_days": 18
        },
        {
            "part_number": "VALVE-CTRL-04",
            "description": "Pneumatic Solenoid Control Valve",
            "equipment_system": "Bridge Automation & Control",
            "primary_supplier": "Aegis Maritime Supplies",
            "unit_price_usd": 950.00,
            "warehouse_location": "Rotterdam",
            "stock_on_hand": 15,
            "min_safety_stock": 5,
            "lead_time_days": 4
        },
        {
            "part_number": "SEAL-PROP-09",
            "description": "Stern Tube Propulsion Shaft Mechanical Seal",
            "equipment_system": "Propulsion & Shafting",
            "primary_supplier": "Nordik Marine Spares",
            "unit_price_usd": 1400.00,
            "warehouse_location": "Dubai",
            "stock_on_hand": 6,
            "min_safety_stock": 6,
            "lead_time_days": 8
        },
        {
            "part_number": "FILT-LUBE-50",
            "description": "High-Capacity Lubricating Oil Filter Cartridge",
            "equipment_system": "Auxiliary Lubrication",
            "primary_supplier": "Aegis Maritime Supplies",
            "unit_price_usd": 320.00,
            "warehouse_location": "Singapore",
            "stock_on_hand": 25,
            "min_safety_stock": 10,
            "lead_time_days": 3
        },
        {
            "part_number": "GEN-INJ-12",
            "description": "Auxiliary Generator Fuel Injection Nozzle",
            "equipment_system": "Diesel Generator Powerplant",
            "primary_supplier": "Oceanic Engineering Ltd",
            "unit_price_usd": 680.00,
            "warehouse_location": "Rotterdam",
            "stock_on_hand": 12,
            "min_safety_stock": 6,
            "lead_time_days": 14
        }
    ]

    df = pd.DataFrame(parts_data)
    df.to_csv(os.path.join(target_dir, "spare_parts_catalog.csv"), index=False)

    # 2. supplier_information.pdf
    doc_supp = pymupdf.open()
    page_s = doc_supp.new_page()
    supp_text = """PACIFIC HORIZON MARITIME - APPROVED SUPPLIER DIRECTORY
DOCUMENT REF: DIR-SUPP-2024 | FLEET TECHNICAL SPECIFICATIONS

SECTION 1: APPROVED VENDOR OVERVIEW
All marine spare parts and technical ship supplies must be procured exclusively from accredited vendors evaluated under ISO 9001 and maritime safety compliance standards.

SECTION 2: VENDOR PROFILES & PERFORMANCE RATINGS
2.1 Nordik Marine Spares (Oslo / Rotterdam Hub)
- Quality Rating: A+ (98% compliance score)
- Specialties: Main engine heavy components, pumps, mechanical seals, turbochargers.
- Standard Payment Terms: Net 30 days from commercial invoice.
- Delivery Methods: Standard sea freight (10 to 14 days transit); regional hub dispatch (48 hours).

2.2 Aegis Maritime Supplies (Singapore Hub)
- Quality Rating: A (94% compliance score)
- Specialties: Valves, sensors, instrumentation, urgent consumable filtration.
- Standard Payment Terms: Net 45 days.
- Delivery Methods: Express air freight (3 to 5 business days to major worldwide seaports) with an authorized 15% courier surcharge.

2.3 Oceanic Engineering Ltd (Busan / Shanghai Hub)
- Quality Rating: A- (91% compliance score)
- Specialties: Cylinder liners, engine structural castings, generator injectors.
- Standard Payment Terms: Net 45 days post delivery inspection.
- Commercial Discount: Automatic 5% volume discount for purchase orders exceeding $5,000.00 USD.

SECTION 3: MANDATORY WARRANTY REQUIREMENTS
Approved suppliers must provide a minimum warranty period of twelve (12) months from installation date or eighteen (18) months from delivery date to warehouse, whichever occurs first. Defective components must be replaced within seven (7) business days at vendor expense.
"""
    page_s.insert_text((50, 60), supp_text, fontsize=10, lineheight=1.3)
    doc_supp.save(os.path.join(target_dir, "supplier_information.pdf"))
    doc_supp.close()

    # 3. procurement_guidelines.pdf
    doc_guide = pymupdf.open()
    page_g = doc_guide.new_page()
    guide_text = """PACIFIC HORIZON MARITIME - VESSEL PROCUREMENT GUIDELINES
DOCUMENT REF: POL-PROC-2024 | FLEET COMPLIANCE & AUTHORIZATION MATRIX

SECTION 1: GENERAL PROCUREMENT OBJECTIVES
This policy governs technical procurement of machinery, spare parts, and drydock consumables for all vessels in the fleet. Cost efficiency must never compromise vessel seaworthiness or SOLAS compliance.

SECTION 2: THREE-QUOTE RULE & SOLE-SOURCE EXCEPTIONS
2.1 Three-Quote Standard: All purchase orders over $5,000 USD require three (3) independent competitive quotations from approved suppliers.
2.2 OEM Sole-Source Exception: Sole-source procurement is permitted only when parts are proprietary OEM certified components necessary to preserve classification society certification.

SECTION 3: FINANCIAL DELEGATION OF AUTHORITY (DOA)
3.1 Chief Engineer Ceiling: Up to $2,500.00 USD for standard catalog consumables and routine voyage maintenance without superintendent approval.
3.2 Technical Superintendent Ceiling: Up to $25,000.00 USD per purchase order.
3.3 Fleet Technical Director Ceiling: Up to $50,000.00 USD.
3.4 Dual Sign-Off: Any expenditure exceeding $50,000.00 USD requires dual authorization from the Fleet Technical Director and Chief Financial Officer (CFO).

SECTION 4: EMERGENCY PROCUREMENT PROTOCOL
5.1 Blackout / Seaworthiness Threat: In the event of main engine breakdown, blackout at sea, or safety conditions endangering the vessel, the Master and Chief Engineer are authorized to approve emergency dispatch up to $10,000.00 USD with immediate written notification to the Superintendent within 12 hours.

SECTION 5: STRICT PROHIBITIONS & COMPLIANCE
6.1 Financial Transactions: The AI Procurement Assistant is strictly prohibited from executing direct bank wire transfers, automated credit card payments, or currency conversions.
6.2 Anti-Bribery: Unofficial customs clearance facilitation payments, unreceipted port dispatch fees, and bribes are strictly prohibited and violate international maritime anti-corruption laws.
"""
    page_g.insert_text((50, 60), guide_text, fontsize=10, lineheight=1.3)
    doc_guide.save(os.path.join(target_dir, "procurement_guidelines.pdf"))
    doc_guide.close()
    print(f"Successfully generated Procurement documents in: {target_dir}")

if __name__ == "__main__":
    create_procurement_documents("demos/procurement_assistant/documents")
