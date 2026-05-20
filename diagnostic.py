"""
AsaanRaabta AI - Full System Diagnostic
Checks: LLM, providers data, location NLP, time NLP, CSV logging, followups
"""
import json, os, sys, re

print("=" * 60)
print("  AsaanRaabta AI - SYSTEM DIAGNOSTIC")
print("=" * 60)

# ---- 1. Providers JSON ----
print("\n[1] CHECKING providers.json ...")
try:
    with open("providers.json", "r", encoding="utf-8") as f:
        providers = json.load(f)
    print(f"    OK - Loaded {len(providers)} providers")
    cities   = set(p.get("city") for p in providers)
    services = set(p.get("service") for p in providers)
    locs     = set(p.get("location") for p in providers)
    print(f"    Cities:   {cities}")
    print(f"    Services: {services}")
    print(f"    Locations ({len(locs)}): {sorted(locs)}")
except Exception as e:
    print(f"    FAIL - {e}")

# ---- 2. Gemini LLM ----
print("\n[2] CHECKING Gemini LLM connection ...")
try:
    from google import genai
    GEMINI_API_KEY = "AIzaSyBpiblcBiA0g5minCADsgiDKzpUaIWPmRk"
    client = genai.Client(api_key=GEMINI_API_KEY)
    chat = client.chats.create(model="gemini-2.5-flash")
    resp = chat.send_message('Reply with exactly: CONNECTED')
    print(f"    OK - Gemini responded: {resp.text.strip()}")
except Exception as e:
    print(f"    FAIL - {e}")

# ---- 3. Orchestrator Import ----
print("\n[3] CHECKING orchestrator.py imports ...")
try:
    sys.path.insert(0, os.getcwd())
    from orchestrator import AntigravityOrchestrator
    o = AntigravityOrchestrator()
    print(f"    OK - AntigravityOrchestrator loaded")
    print(f"    LLM active: {o.use_llm}")
    print(f"    Providers loaded: {len(o.providers)}")
except Exception as e:
    print(f"    FAIL - {e}")
    sys.exit(1)

# ---- 4. Location NLP ----
print("\n[4] CHECKING location extraction ...")
location_tests = [
    ("Barrage Colony mein AC chahiye",        "Barrage Colony"),
    ("Gharibabad mein plumber",               "Gharibabad"),
    ("Old Sukkur mein bijli wala",            "Old Sukkur"),
    ("Township mein tutor chahiye",           "Sukkur Township"),
    ("Minara Road par kaam",                  "Minara Road"),
    ("Ghanta Ghar area mein electrician",     "Ghanta Ghar"),
    ("Military Road mein AC repair",          "Military Road"),
    ("Bunder Road mein plumber chahiye",      "Bunder Road"),
    ("Sukkur Bypass ke paas AC technician",   "Sukkur Bypass"),
    ("Site Area mein bijli wiring",           "Site Area"),
    ("Airport Road par AC service",           "Airport Road"),
]
loc_pass = 0
for text, expected in location_tests:
    got = o._extract_location(text)
    status = "PASS" if got == expected else f"FAIL (got: {got})"
    if "PASS" in status: loc_pass += 1
    print(f"    {status} | '{text[:40]}' -> expected '{expected}'")
print(f"    Location score: {loc_pass}/{len(location_tests)}")

# ---- 5. Time NLP ----
print("\n[5] CHECKING time extraction ...")
time_tests = [
    ("kal subah AC technician chahiye",  "10:00 AM"),
    ("shaam ko plumber chahiye",         "04:00 PM"),
    ("10am pe electrician",              "10:00 AM"),
    ("4 baj pe plumber",                 "04:00 PM"),
    ("morning mein tutor chahiye",       "10:00 AM"),
    ("raat ko home nurse",               "06:00 PM"),
    ("2pm ko AC repair",                 "02:00 PM"),
    ("12 baj ke baad plumber",           "12:00 PM"),
]
time_pass = 0
for text, expected in time_tests:
    got = o._extract_time(text)
    status = "PASS" if got == expected else f"FAIL (got: {got})"
    if "PASS" in status: time_pass += 1
    print(f"    {status} | '{text[:40]}' -> expected '{expected}'")
print(f"    Time score: {time_pass}/{len(time_tests)}")

# ---- 6. Service NLP ----
print("\n[6] CHECKING service extraction ...")
svc_tests = [
    ("AC technician chahiye",      "AC Technician"),
    ("bijli wala chahiye",         "Electrician"),
    ("plumber chahiye",            "Plumber"),
    ("tutor chahiye mujhe",        "Tutor"),
    ("home nurse chahiye",         "Home Nurse"),
    ("AC repair",                  "AC Technician"),
    ("I need an electrician",      "Electrician"),
    ("pipe leak fix karo",         "Plumber"),
]
svc_pass = 0
for text, expected in svc_tests:
    got = o._extract_service(text)
    status = "PASS" if got == expected else f"FAIL (got: {got})"
    if "PASS" in status: svc_pass += 1
    print(f"    {status} | '{text[:40]}' -> expected '{expected}'")
print(f"    Service score: {svc_pass}/{len(svc_tests)}")

# ---- 7. Full Pipeline Test ----
print("\n[7] CHECKING full pipeline (fallback mode) ...")
o.use_llm = False
pipeline_tests = [
    "Mujhe kal subah Barrage Colony mein AC technician chahiye",
    "Gharibabad mein plumber chahiye shaam ko",
    "Old Sukkur mein electrician chahiye 4 baj",
    "Township mein tutor chahiye 10am",
    "Minara Road par bijli ka kaam chahiye",
    "Ghanta Ghar mein AC repair karna hai",
]
for t in pipeline_tests:
    r = o.process_request(t)
    if "provider" in r:
        p = r["provider"]
        print(f"    PASS | {t[:45]}")
        print(f"           -> {p.get('name')} | {p.get('location')} | {p.get('matched_slot')}")
    else:
        print(f"    FAIL | {t[:45]} -> {r.get('error')}")

# ---- 8. CSV logging ----
print("\n[8] CHECKING bookings.csv ...")
if os.path.exists("bookings.csv"):
    with open("bookings.csv", "r", encoding="utf-8") as f:
        lines = f.readlines()
    print(f"    OK - File exists, {len(lines)} rows (including header)")
else:
    print("    NOTE - bookings.csv not yet created (will be on first booking)")

# ---- 9. Followups JSON ----
print("\n[9] CHECKING followups.json ...")
if os.path.exists("followups.json"):
    with open("followups.json", "r", encoding="utf-8") as f:
        fu = json.load(f)
    print(f"    OK - {len(fu)} follow-up workflows logged")
else:
    print("    NOTE - followups.json not yet created (will be on first booking)")

print("\n" + "=" * 60)
print("  DIAGNOSTIC COMPLETE")
print("=" * 60)
