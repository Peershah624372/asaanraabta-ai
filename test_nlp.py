from orchestrator import AntigravityOrchestrator
o = AntigravityOrchestrator()
o.use_llm = False  # test rule-based fallback

tests = [
    "Mujhe kal subah Barrage Colony mein AC technician chahiye",
    "Gharibabad mein plumber chahiye shaam ko",
    "Old Sukkur mein electrician chahiye 4 baj",
    "Township mein tutor chahiye 10am",
    "Minara Road par bijli ka kaam chahiye",
    "Ghanta Ghar mein AC repair",
]

for t in tests:
    r = o.process_request(t)
    p = r.get("provider", {})
    print("Input:", t)
    print("  Provider:", p.get("name"))
    print("  Location:", p.get("location"))
    print("  Slot:", p.get("matched_slot"))
    print()
