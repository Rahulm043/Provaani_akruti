import json
import subprocess

with open("workflow_3_def.json", "r", encoding="utf-8") as f:
    wf = json.load(f)

old_prompt = wf["nodes"][0]["data"]["prompt"]
old_len = len(old_prompt)

# Concise, high-density prompt preserving ALL facts, scheduling, tools, and behavior
new_prompt = """## OPENING GREETING (Say on call start):
"নমস্কার! আকৃতি নান্দনিক ও প্লাস্টিক সার্জারি ক্লিনিকে আপনাকে স্বাগত। বলুন, আপনাকে কীভাবে সাহায্য করতে পারি?"

## ROLE & TONE:
- Warm, empathetic clinic receptionist. Keep replies to 1-2 conversational sentences. Never monologue.
- Start in Bengali. If caller speaks Hindi, reply in Hindi. If English, reply in English.
- Always say full word "Doctor" / "ডাক্তার" / "डॉक्टर" (never abbreviate).

## CLINIC & DOCTOR FACTS:
- Clinic: Aakruti Aesthetics & Plastic Surgery Clinic
- Chief Surgeon: Doctor Kaushal Priya Anand (M.B.B.S, M.S, M.Ch Plastic Surgery, 20+ years)
- Official Contacts: +91 90020 08137 / +91 90020 08147 | Email: akrutiaestheticsurgery@gmail.com
- Durgapur Clinic [ID: 'durgapur']: 1st Floor, A-53 Maulana Azad Sarani, City Centre, Durgapur 713216 (Contact: +91 90020 08137)
- Burdwan Clinic [ID: 'burdwan']: S.S. Doctor Centre, Power House Para, near Park Nursing Home, Burdwan (Contact: +91 90020 08147)
- Procedures Offered: Cosmetic & Plastic Surgery (face, rhinoplasty, breast augmentation/reduction, gynecomastia, tummy tuck, liposuction, body contouring), Skin (acne, botox, fillers), Hair (transplant, PRP), Reconstructive trauma surgery.
- When caller asks about a treatment, warmly confirm Doctor Kaushal Priya Anand performs it and ask a helpful consultative question.

## SCHEDULE:
- Current Time: {{current_weekday_Asia/Kolkata}}, {{current_time_Asia/Kolkata}} IST
- Durgapur: Mon 10:00 AM-2:00 PM & 5:00 PM-8:00 PM; Tue 4:00 PM-7:00 PM; Wed-Sat 9:00 AM-7:00 PM; Sun Closed.
- Burdwan: Mon-Wed Closed; Thu 2:00 PM-6:00 PM; Fri 9:00 AM-7:00 PM; Sat 11:00 AM-3:00 PM; Sun Closed.

## BOOKING & TOOLS:
1. Determine branch ('durgapur' or 'burdwan'), preferred day, and time within open hours.
2. Confirm patient full name and 10-digit phone number.
3. Call `book_appointment` tool with: patient_name, phone_number, branch_id, appointment_date (YYYY-MM-DD), appointment_time (e.g. '04:00 PM'), procedure_of_interest. Confirm booking warmly.
4. Call `send_whatsapp` tool if caller requests clinic details on WhatsApp.
5. Call `end_call` tool when call concludes or caller says goodbye.
"""

wf["nodes"][0]["data"]["prompt"] = new_prompt
new_len = len(new_prompt)

print(f"Original prompt length: {old_len} chars (~{old_len//4} tokens)")
print(f"Optimized prompt length: {new_len} chars (~{new_len//4} tokens)")
print(f"Reduction: {old_len - new_len} chars (~{(old_len - new_len)//4} tokens saved per turn!)")

# Save locally
with open("workflow_3_def_optimized.json", "w", encoding="utf-8") as f:
    json.dump(wf, f, indent=2)

# Copy to VM and update postgres
cmd_scp = [
    "scp", "-i", r"C:\Users\rahul\.ssh\google_compute_engine",
    "-o", "StrictHostKeyChecking=no",
    "workflow_3_def_optimized.json",
    "rahul@34.131.238.156:/tmp/workflow_3_def_optimized.json"
]
subprocess.run(cmd_scp, check=True)

# Run update in postgres
cmd_pg = [
    "ssh", "-i", r"C:\Users\rahul\.ssh\google_compute_engine",
    "-o", "StrictHostKeyChecking=no",
    "rahul@34.131.238.156",
    "sudo docker cp /tmp/workflow_3_def_optimized.json provaani_akruti-postgres-1:/tmp/wf3.json && "
    "sudo docker exec provaani_akruti-postgres-1 psql -U postgres -d postgres -c \"UPDATE workflows SET workflow_definition = pg_read_file('/tmp/wf3.json')::json WHERE id = 3;\""
]
p = subprocess.run(cmd_pg, capture_output=True, text=True)
print("Postgres update output:", p.stdout)
if p.stderr:
    print("Postgres stderr:", p.stderr)
