import json
import re
import csv
import os
import random

# -------------------------------------------------------------------
# GEMINI API KEY - Optional. If quota exceeded, falls back to rules.
# -------------------------------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# ------------------------------------------------------------------
# Location map: keyword patterns -> canonical display name
# Must match location values in providers.json exactly
# ------------------------------------------------------------------
LOCATION_MAP = [
    (r'\b(barrage\s*colony|barrij\s*colony|baraj)\b',        "Barrage Colony"),
    (r'\b(gharibabad|gharibaad|ghareebabad)\b',               "Gharibabad"),
    (r'\b(old\s*sukkur|purani\s*sukkur|puraano\s*sukkur)\b', "Old Sukkur"),
    (r'\b(sukkur\s*township|township)\b',                     "Sukkur Township"),
    (r'\b(military\s*road|military)\b',                       "Military Road"),
    (r'\b(minara\s*road|minara)\b',                           "Minara Road"),
    (r'\b(bunder\s*road|bunder)\b',                           "Bunder Road"),
    (r'\b(ghanta\s*ghar|ghanta|clock\s*tower)\b',             "Ghanta Ghar"),
    (r'\b(bypass|sukkur\s*bypass)\b',                         "Sukkur Bypass"),
    (r'\b(site\s*area|site)\b',                               "Site Area"),
    (r'\b(airport\s*road|airport)\b',                         "Airport Road"),
]

# ------------------------------------------------------------------
# Time map: keyword patterns -> canonical time slot strings
# These MUST match the format in providers.json (e.g. "09:00 AM")
# ------------------------------------------------------------------
TIME_MAP = [
    (r'\b(9\s*baj|9\s*am|9:00|nauh\s*baj|nau\s*baj)\b',     "09:00 AM"),
    (r'\b(10\s*baj|10\s*am|10:00|das\s*baj)\b',              "10:00 AM"),
    (r'\b(11\s*baj|11\s*am|11:00|gyara\s*baj)\b',            "11:00 AM"),
    (r'\b(12\s*baj|12\s*pm|12:00|baara\s*baj|dopehar)\b',    "12:00 PM"),
    (r'\b(1\s*baj|1\s*pm|ek\s*baj)\b',                       "01:00 PM"),
    (r'\b(2\s*baj|2\s*pm|do\s*baj)\b',                       "02:00 PM"),
    (r'\b(3\s*baj|3\s*pm|teen\s*baj)\b',                     "03:00 PM"),
    (r'\b(4\s*baj|4\s*pm|char\s*baj)\b',                     "04:00 PM"),
    (r'\b(5\s*baj|5\s*pm|paanch\s*baj)\b',                   "05:00 PM"),
    (r'\b(6\s*baj|6\s*pm|cheh\s*baj)\b',                     "06:00 PM"),
    # Morning / afternoon / night blocks
    (r'\b(morning|subah|subhan|kal\s*subah|aaj\s*subah|sver)\b', "10:00 AM"),
    (r'\b(afternoon|shaam|evening|baad\s*dopehar)\b',             "04:00 PM"),
    (r'\b(night|raat|sham\s*ko)\b',                               "06:00 PM"),
]


class AntigravityOrchestrator:
    """Core Orchestration platform — Antigravity-style multi-agent pipeline."""

    def __init__(self):
        # Load providers
        try:
            with open('providers.json', 'r', encoding='utf-8') as f:
                self.providers = json.load(f)
            print(f"[Orchestrator] Loaded {len(self.providers)} providers.")
        except FileNotFoundError:
            self.providers = []
            print("[Orchestrator] WARNING: providers.json not found.")

        self.logs = []

        # Try to initialise Gemini — gracefully fall back on any failure
        self.use_llm = False
        self.genai_client = None
        self.chat_session = None

        if GEMINI_API_KEY:
            try:
                from google import genai  # noqa: PLC0415
                self.genai_client = genai.Client(api_key=GEMINI_API_KEY)
                self.model_name = "gemini-2.5-flash"
                self.chat_session = self.genai_client.chats.create(model=self.model_name)
                self.use_llm = True
                print("[Orchestrator] Gemini 2.5 Flash initialised.")
            except Exception as exc:
                print(f"[Orchestrator] Gemini init failed ({exc}). Rule-based fallback active.")
        else:
            print("[Orchestrator] Running in fallback NLP mode.")

    # ---------------------------------------------------------------
    def log_step(self, agent_name, action):
        entry = f"[{agent_name}] {action}"
        self.logs.append(entry)
        print(entry)

    def tool_google_maps_api(self, user_location, provider_location):
        self.log_step(
            "Antigravity Tools",
            f"Google Maps API: distance from '{user_location}' to '{provider_location}' calculated."
        )
        return {"status": "success", "routing": "optimal"}

    def tool_twilio_sms_api(self, phone_number, message):
        self.log_step(
            "Antigravity Tools",
            f"Twilio SMS dispatched to {phone_number}: '{message[:70]}...'"
        )
        return {"status": "delivered"}

    # ---------------------------------------------------------------
    # NLP HELPERS
    # ---------------------------------------------------------------
    def _extract_location(self, text):
        lowered = text.lower()
        for pattern, canonical in LOCATION_MAP:
            if re.search(pattern, lowered):
                return canonical
        return None

    def _extract_time(self, text):
        """Returns a canonical time string matching providers.json (e.g. '10:00 AM') or None."""
        lowered = text.lower()

        # Explicit HH or H am/pm pattern  (e.g. "9am", "10 am", "2pm", "4:30pm")
        m = re.search(r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b', lowered)
        if m:
            h   = int(m.group(1))
            mn  = m.group(2) or '00'
            sfx = m.group(3).upper()
            # Normalise to 12-hour display used in providers.json
            return f"{h:02d}:{mn} {sfx}"

        # Keyword map
        for pattern, slot in TIME_MAP:
            if re.search(pattern, lowered):
                return slot

        return None

    def _extract_service(self, text):
        lowered = text.lower()
        ac_kw     = r'\b(ac|air\s*condition|airconditioner|cooling|thanda|technician)\b'
        elec_kw   = r'\b(electrician|bijli|biji|wiring|light|pankha|electric)\b'
        plumb_kw  = r'\b(plumber|pani|paani|nal|leak|pipe|plumbing)\b'
        tutor_kw  = r'\b(tutor|teacher|padhai|ustad)\b'
        nurse_kw  = r'\b(nurse|nursing|injection|drip)\b'

        if re.search(ac_kw,    lowered): return "AC Technician"
        if re.search(elec_kw,  lowered): return "Electrician"
        if re.search(plumb_kw, lowered): return "Plumber"
        if re.search(tutor_kw, lowered): return "Tutor"
        if re.search(nurse_kw, lowered): return "Home Nurse"
        return None

    # ---------------------------------------------------------------
    # AGENT 1 — INTENT
    # ---------------------------------------------------------------
    def intent_agent(self, user_input):
        self.log_step("Intent Agent", f"Analyzing: '{user_input}'")

        # ---- LLM path (Gemini) ----
        if self.use_llm and self.chat_session:
            self.log_step("Intent Agent", "Calling Gemini 2.5 Flash for NLP...")
            prompt = f"""
You are 'AsaanRaabta AI', an assistant for informal economy services in Sukkur, Pakistan.
Services available: AC Technician, Electrician, Plumber, Tutor, Home Nurse.
Analyze this user message: "{user_input}"

Decide: SERVICE REQUEST or GENERAL CHAT.

If SERVICE REQUEST → extract:
- service (exactly one of the 5 above)
- location (neighbourhood in Sukkur: Barrage Colony, Gharibabad, Old Sukkur, Sukkur Township, Military Road, Minara Road, Bunder Road, Ghanta Ghar, Sukkur Bypass, Site Area, Airport Road — or null)
- time (exact slot like "10:00 AM", "04:00 PM" — or null)
Return ONLY valid JSON, no markdown:
{{"type":"service","service":"...","location":"...","time":"..."}}

If GENERAL CHAT:
Return ONLY:
{{"type":"chat","response":"friendly reply in user's language (Urdu/Roman Urdu/English)"}}
"""
            try:
                resp = self.chat_session.send_message(prompt)
                raw  = resp.text.strip()
                raw  = re.sub(r'^```(?:json)?', '', raw).rstrip('`').strip()
                data = json.loads(raw)
                if data.get('type') == 'chat':
                    return {"is_chat": True, "chat_response": data.get('response', '')}
                service   = data.get('service')
                location  = data.get('location') or self._extract_location(user_input)
                time_slot = data.get('time')     or self._extract_time(user_input)
                self.log_step("Intent Agent",
                    f"Gemini extracted → Service: {service}, Location: {location}, Time: {time_slot}")
                return {"service": service, "city": "Sukkur",
                        "location": location, "time": time_slot}
            except Exception as exc:
                error_text = str(exc).lower()

                # Quota exceeded
                if "429" in error_text or "quota" in error_text:
                    self.log_step(
                        "Intent Agent",
                        "Gemini quota exceeded. Switching to rule-based NLP."
                        )

                # Invalid API key
                elif "api key" in error_text or "permission" in error_text:
                    self.log_step(
                        "Intent Agent",
                        "Invalid Gemini API key. Rule-based NLP activated."
                    )

                # Network / connection issue
                elif "connection" in error_text or "timeout" in error_text:
                    self.log_step(
                        "Intent Agent",
                        "Gemini connection issue. Using fallback NLP."
                    )

                # Unknown issue
                else:
                    self.log_step(
                        "Intent Agent",
                        f"Gemini failed: {exc}"
                    )

        # Disable Gemini for current session
        self.use_llm = False

        # ---- RULE-BASED FALLBACK ----
        service = self._extract_service(user_input)
        if not service:
            self.log_step("Intent Agent", "No service keyword → treating as general chat.")
            return {"is_chat": True, "chat_response": self.mock_llm_chat(user_input)}

        location  = self._extract_location(user_input)
        time_slot = self._extract_time(user_input)
        self.log_step("Intent Agent",
            f"Rule-based → Service: {service}, Location: {location}, Time: {time_slot}")
        return {"service": service, "city": "Sukkur",
                "location": location, "time": time_slot}

    # ---------------------------------------------------------------
    # AGENT 2 — MATCHING
    # ---------------------------------------------------------------
    def matching_agent(self, intent_data):
        self.log_step("Matching Agent", "Filtering provider database...")
        try:
            service        = intent_data.get('service')
            location       = intent_data.get('location')
            requested_time = intent_data.get('time')

            if not service:
                return None

            # Filter by service
            matches = [p for p in self.providers
                       if p.get('service', '').lower() == service.lower()]

            if not matches:
                self.log_step("Matching Agent", f"No providers found for '{service}'.")
                return None

            self.log_step("Matching Agent",
                f"{len(matches)} providers for '{service}'. Scoring...")

            def score(p):
                loc_boost = 0
                if location and location.lower() not in ('unknown', 'null', ''):
                    p_loc = p.get('location', '').lower()
                    u_loc = location.lower()
                    if u_loc in p_loc or p_loc in u_loc:
                        loc_boost = -200
                        self.tool_google_maps_api(location, p.get('location'))
                return (loc_boost + p.get('distance_km', 999),
                        -p.get('rating', 0),
                        -p.get('experience_years', 0))

            matches.sort(key=score)

            # Find slot match
            best = None
            if requested_time and requested_time not in ('ASAP', None):
                self.log_step("Matching Agent", f"Looking for slot '{requested_time}'...")
                req_upper = requested_time.upper().strip()
                for p in matches:
                    slots = p.get('availability', [])
                    hit = [s for s in slots
                            if req_upper.strip() == s.upper().strip()]
                    if hit:
                        best = p.copy()
                        best['matched_slot'] = hit[0]
                        self.log_step("Matching Agent",
                            f"Slot match: {best['name']} @ {best['matched_slot']}")
                        break
                if not best:
                    self.log_step("Matching Agent",
                        "No exact time match — selecting best available provider.")

            if not best:
                best  = matches[0].copy()
                slots = best.get('availability', [])
                best['matched_slot'] = slots[0] if slots else "ASAP"

            best['alternatives'] = [m.copy() for m in matches[1:3]]

            self.log_step("Matching Agent",
                f"Selected: {best['name']} | ⭐ {best['rating']} | "
                f"{best['experience_years']} yrs | {best['distance_km']} km | "
                f"Slot: {best['matched_slot']}")
            return best

        except Exception as exc:
            self.log_step("Matching Agent", f"Error: {exc}")
            return None

    # ---------------------------------------------------------------
    # AGENT 3 — ACTION  (Booking + CSV + Follow-up)
    # ---------------------------------------------------------------
    def action_agent(self, provider):
        try:
            self.log_step("Action Agent",
                f"Initiating booking with {provider.get('name', 'provider')}...")

            # Simulate autonomous re-routing (30% chance when alternatives exist)
            alternatives = provider.get('alternatives', [])
            if False and alternatives:
                self.log_step("Action Agent",
                    "⚠️ Simulating provider unavailability — auto-rerouting...")
                alt = alternatives[0].copy() if isinstance(alternatives[0], dict) else {}
                if alt:
                    slots = alt.get('availability', ['ASAP'])
                    alt['matched_slot'] = slots[0] if slots else "ASAP"
                    provider = alt
                    self.log_step("Action Agent",
                        f"✅ Auto-rerouted to: {provider.get('name', 'Unknown')}")

            slot        = provider.get('matched_slot', 'ASAP')
            provider_id = provider.get('id', 'UNK')

            # --- State change: remove booked slot from providers.json ---
            try:
                with open('providers.json', 'r', encoding='utf-8') as f:
                    current_providers = json.load(f)
            except Exception:
                current_providers = self.providers[:]

            # --- Save booked slot separately ---
            booked_file = 'booked_slots.json'

            try:
                if os.path.exists(booked_file):
                    with open(booked_file, 'r', encoding='utf-8') as f:
                        booked_slots = json.load(f)
                else:
                    booked_slots = []

                booked_slots.append({
                    "provider_id": provider_id,
                    "slot": slot
                })

                with open(booked_file, 'w', encoding='utf-8') as f:
                    json.dump(booked_slots, f, indent=2)

                self.log_step(
                    "Action Agent",
                    f"Booked slot saved safely for provider {provider_id}."
    )

            except Exception as exc:
                self.log_step(
                    "Action Agent",
                    f"Could not save booked slot: {exc}"
                )

            # --- Write to bookings.csv ---
            csv_file   = 'bookings.csv'
            file_exists = os.path.isfile(csv_file)
            booking_id  = f"{provider_id}-{slot.replace(':', '').replace(' ', '')}"

            with open(csv_file, mode='a', newline='', encoding='utf-8') as fh:
                writer = csv.writer(fh)
                if not file_exists:
                    writer.writerow([
                        'Booking ID', 'Provider Name', 'Service',
                        'City', 'Location', 'Time Slot',
                        'Base Rate', 'Contact', 'Status'
                    ])
                writer.writerow([
                    booking_id,
                    provider.get('name', 'N/A'),
                    provider.get('service', 'N/A'),
                    provider.get('city', 'Sukkur'),
                    provider.get('location', 'N/A'),
                    slot,
                    f"Rs. {provider.get('base_rate', 'N/A')}",
                    provider.get('contact_number', 'N/A'),
                    'Confirmed'
                ])

            self.log_step("Action Agent",
                f"Booking logged to bookings.csv (ID: {booking_id})")

            # --- Simulated SMS ---
            self.tool_twilio_sms_api(
                provider.get('contact_number', '+923000000000'),
                f"Booking confirmed with {provider['name']} for {slot}."
            )

            # --- Follow-up scheduling ---
            follow_up = {
                "booking_id":    booking_id,
                "provider_name": provider.get('name'),
                "location":      provider.get('location'),
                "schedule": [
                    {
                        "event":   "Reminder",
                        "time":    "1 hour before",
                        "status":  "Scheduled",
                        "message": f"Yaad dihani: {provider['name']} 1 ghante mein aayega."
                    },
                    {
                        "event":   "Status Update",
                        "time":    "At appointment",
                        "status":  "Scheduled",
                        "message": f"{provider['name']} raaste mein hai."
                    },
                    {
                        "event":   "Completion",
                        "time":    "1 hour after",
                        "status":  "Scheduled",
                        "message": "Kya kaam mukammal ho gaya? Jawab dijiye: HAAN ya NAHI."
                    }
                ]
            }

            try:
                if os.path.exists('followups.json'):

                    with open('followups.json', 'r', encoding='utf-8') as f:
                        all_followups = json.load(f)

                else:
                    all_followups = []
            except Exception:
                all_followups = []

                        # Prevent duplicate follow-ups
            existing_ids = [f.get("booking_id") for f in all_followups]

            if booking_id not in existing_ids:
                all_followups.append(follow_up)

                self.log_step(
                    "Follow-Up Agent",
                    f"Follow-up workflow created for booking {booking_id}."
                )
            else:
                self.log_step(
                    "Follow-Up Agent",
                    f"Follow-up already exists for booking {booking_id}. Skipping duplicate."
                )
            with open('followups.json', 'w', encoding='utf-8') as f:
                json.dump(all_followups, f, indent=2, ensure_ascii=False)

            self.log_step("Follow-Up Agent",
                f"Follow-up workflow saved (Booking: {booking_id})")

            # Sync booking into LLM memory (if active)
            if self.use_llm and self.chat_session:
                try:
                    self.chat_session.send_message(
                        f"System: Booking confirmed — {provider['name']} at {slot} "
                        f"in {provider.get('location')}. Remember this for follow-ups."
                    )
                except Exception:
                    pass

            return {
                "provider":     provider,
                "booking_id":   booking_id,
                "booking_time": slot,
                "status":       "Confirmed",
                "message":      f"Booking confirmed with {provider['name']} for {slot}."
            }

        except Exception as exc:
            self.log_step("Action Agent", f"Critical error: {exc}")
            return {"error": f"Booking failed: {exc}", "logs": self.logs}

    # ---------------------------------------------------------------
    # MAIN PIPELINE
    # ---------------------------------------------------------------
    def process_request(self, user_input, user_name="User"):
        self.logs = []
        try:
            intent = self.intent_agent(user_input)

            if intent.get('is_chat'):
                return {"is_chat": True, "message": intent['chat_response'], "logs": self.logs}

            if not intent.get('service'):
                return {"error": "Maaf karna, kaunsi service chahiye yeh samajh nahi aaya.",
                        "logs": self.logs}

            provider = self.matching_agent(intent)
            if not provider:
                return {"error": "Is waqt is ilaqe mein koi provider available nahi hai.",
                        "logs": self.logs}

            service   = intent.get('service')   or 'Service'
            location  = intent.get('location')  or 'Sukkur'
            time_slot = intent.get('time')      or 'ASAP'

            msg = (
                f"**Service Request:** {service}\n\n"
                f"**Location:** {location}\n\n"
                f"**Time:** {time_slot}\n\n"
                f"**Recommended Provider:** {provider['name']} "
                f"({provider.get('distance_km')} km away, ⭐ {provider.get('rating')})\n"
                f"*(Experience: {provider.get('experience_years', 0)} yrs | "
                f"Base Rate: Rs. {provider.get('base_rate', 'N/A')})*\n\n"
                f"**Reasoning:** Nearest available provider in {provider.get('location')}, "
                f"ranked by highest rating and experience."
            )

            return {"provider": provider, "message": msg, "logs": self.logs}

        except Exception as exc:
            self.log_step("Orchestrator", f"Pipeline error: {exc}")
            return {"error": "System error. Please try again.", "logs": self.logs}

    # ---------------------------------------------------------------
    # MOCK CHAT FALLBACK
    # ---------------------------------------------------------------
    def mock_llm_chat(self, user_input):
        low = user_input.lower()
        if re.search(r'\b(salam|assalam|hello|hi|hey|aoa)\b', low):
            return ("Walaikum Assalam! Main AsaanRaabta AI hoon. 😊\n\n"
                    "Kaunsi service chahiye?\n"
                    "**AC Technician · Electrician · Plumber · Tutor · Home Nurse**")
        if re.search(r'\b(kaise|kya\s*hal|theek|kaisa)\b', low):
            return "Alhamdulillah theek hoon! Aap batayein, kya service chahiye?"
        if re.search(r'\b(kaun|naam|kya\s*hai\s*tu|what\s*are\s*you)\b', low):
            return ("Main AsaanRaabta AI hoon — Sukkur ka AI service orchestrator. 🤖\n"
                    "Ghar par service provider dhoondhne mein madad karta hoon.")
        if re.search(r'\b(shukriya|thank|thanks|شکریہ)\b', low):
            return "Khushi hui! Aur koi service chahiye? 😊"
        if re.search(r'\b(bye|khuda\s*hafiz|allah\s*hafiz)\b', low):
            return "Allah Hafiz! AsaanRaabta AI pe phir aaiye. 🙏"
        return ("Maaf karna, main sirf in services ke liye madad kar sakta hoon:\n\n"
                "**AC Technician · Electrician · Plumber · Tutor · Home Nurse**\n\n"
                "Koi service chahiye? Batayein! 😊")
