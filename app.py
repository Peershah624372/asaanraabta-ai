from flask import Flask, render_template, request, jsonify, session
import os
import re
from orchestrator import AntigravityOrchestrator

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", os.urandom(24))

ai_system = AntigravityOrchestrator()


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/reset', methods=['POST'])
def reset():
    """Clears conversation state for a fresh start."""
    session.clear()
    return jsonify({"status": "ok"})


@app.route('/chat', methods=['POST'])
def chat():
    data       = request.get_json(force=True, silent=True) or {}
    user_input = data.get('message', '').strip()
    user_name  = data.get('user_name', 'User')
    ai_system.logs = []

    if not user_input:
        return jsonify({"is_chat": True, "message": "Kuch toh likhein! 😊", "logs": []})

    # Prevent excessively long inputs
    if len(user_input) > 500:
        return jsonify({
            "is_chat": True,
            "message": "Message bohat lamba hai. Thora short likhein 😊",
            "logs": []
        })

    # ------------------------------------------------------------------
    # Conversation State Machine
    # States: None → ask_service → ask_location → ask_time → confirm
    # ------------------------------------------------------------------
    state = session.get('state')

    # ---- STATE: No state — detect intent ----
    if not state:
        intent = ai_system.intent_agent(user_input)

        if intent.get('is_chat'):
            return jsonify({"is_chat": True,
                            "message": intent['chat_response'],
                            "logs": ai_system.logs})

        service   = intent.get('service')
        location  = intent.get('location') if intent.get('location') not in (None, 'Unknown') else None
        time_slot = intent.get('time')     if intent.get('time')     not in (None, 'ASAP')    else None

        session['service']   = service
        session['location']  = location
        session['time']      = time_slot
        session['user_name'] = user_name

        # All three extracted — go straight to matching
        if service and location and time_slot:
            session['state'] = 'confirm'
            return _do_match(user_name)

        # Have service + location, need time
        if service and location:
            session['state'] = 'ask_time'
            return jsonify({
                "is_chat": True,
                "message": (
                    f"Shukriya! **{service}** aur location **{location}** mil gayi. 👍\n\n"
                    f"Ab batayein — **kaunse waqt** chahiye? Masalan:\n"
                    f"- *Subah* (10:00 AM)\n- *Shaam* (4:00 PM)\n"
                    f"- *9am, 2pm* etc.\n- Ya **ASAP** agar abhi chahiye"
                ),
                "logs": ai_system.logs
            })

        # Have service only, need location
        if service:
            session['state'] = 'ask_location'
            return jsonify({
                "is_chat": True,
                "message": (
                    f"Bilkul! **{service}** ki service dhoondh raha hoon. 🔍\n\n"
                    f"Aap Sukkur ke **konse ilaqe** mein hain?\n\n"
                    f"*Barrage Colony · Gharibabad · Old Sukkur · Sukkur Township*\n"
                    f"*Minara Road · Ghanta Ghar · Military Road · Bunder Road*\n"
                    f"*Sukkur Bypass · Site Area · Airport Road*"
                ),
                "logs": ai_system.logs
            })

        # No service — general chat
        session.pop('state', None)
        return jsonify({
            "is_chat": True,
            "message": ai_system.mock_llm_chat(user_input),
            "logs": ai_system.logs
        })

    # ---- STATE: Waiting for service ----
    elif state == 'ask_service':
        service = ai_system._extract_service(user_input)
        if not service:
            return jsonify({
                "is_chat": True,
                "message": (
                    "Maaf karna, samajh nahi aaya. Yeh services available hain:\n\n"
                    "1. **AC Technician** — AC repair, gas refill\n"
                    "2. **Electrician** — bijli, wiring, pankha\n"
                    "3. **Plumber** — pani, pipe, leak\n"
                    "4. **Tutor** — padhai, maths, science\n"
                    "5. **Home Nurse** — injection, drip, elderly care\n\n"
                    "Kaunsi service chahiye?"
                ),
                "logs": ai_system.logs
            })
        session['service'] = service
        session['state']   = 'ask_location'
        return jsonify({
            "is_chat": True,
            "message": (
                f"**{service}** — bilkul! 👍\n\n"
                f"Aap Sukkur ke **konse ilaqe** mein hain?\n\n"
                f"*Barrage Colony · Gharibabad · Old Sukkur · Township*\n"
                f"*Minara Road · Ghanta Ghar · Military Road · Bunder Road ...*"
            ),
            "logs": ai_system.logs
        })

    # ---- STATE: Waiting for location ----
    elif state == 'ask_location':
        location = ai_system._extract_location(user_input)
        if not location:

            # User may be correcting previous location
            if any(word in user_input.lower() for word in [
                "not", "wrong", "change", "instead"
            ]):
                return jsonify({
                    "is_chat": True,
                    "message": (
                        "Theek hai 👍 Apni correct location dobara likhein.\n\n"
                        "Example:\n"
                        "- Barrage Colony\n"
                        "- Gharibabad\n"
                        "- Old Sukkur"
                    ),
                    "logs": ai_system.logs
                })

            return jsonify({
                "is_chat": True,
                "message": (
                    "Yeh location clear nahi hui. Sukkur ke in ilaqon mein se batayein:\n\n"
                    "**Barrage Colony · Gharibabad · Old Sukkur · Sukkur Township**\n"
                    "**Minara Road · Ghanta Ghar · Military Road · Bunder Road**\n"
                    "**Sukkur Bypass · Site Area · Airport Road**"
                ),
                "logs": ai_system.logs
            })
            
        session['location'] = location
        session['state']    = 'ask_time'
        return jsonify({
            "is_chat": True,
            "message": (
                f"**{location}** — noted! 📍\n\n"
                f"**Kaunse waqt** chahiye service?\n\n"
                f"- *Subah* (10 AM) · *Dopehar* (12 PM) · *Shaam* (4 PM)\n"
                f"- Exact time: *9am, 11am, 2pm, 5pm* ...\n"
                f"- Ya **ASAP** agar abhi chahiye"
            ),
            "logs": ai_system.logs
        })

    # ---- STATE: Waiting for time ----
    elif state == 'ask_time':
        time_slot = ai_system._extract_time(user_input)
        if not time_slot and re.search(
                r'\b(asap|abhi|jaldi|jald|now|filhal|foran)\b', user_input.lower()):
            time_slot = 'ASAP'

        if not time_slot:
            return jsonify({
                "is_chat": True,
                "message": (
                    "Waqt clear nahi hua. Koi bhi likhen:\n\n"
                    "- **Subah** / morning (10 AM)\n"
                    "- **Shaam** / evening (4 PM)\n"
                    "- **9am, 11am, 2pm, 5pm** — exact time\n"
                    "- **ASAP** — jitna jaldi ho sake"
                ),
                "logs": ai_system.logs
            })
        session['time']  = time_slot
        session['state'] = 'confirm'
        return _do_match(session.get('user_name', user_name))

    # ---- Fallback ----
    # ---- STATE: Confirm / correction handling ----
    elif state == 'confirm':

        # User correcting location
        new_location = ai_system._extract_location(user_input)

        if new_location:
            session['location'] = new_location

            # Re-run provider matching with updated location
            return _do_match(session.get('user_name', 'User'))

        return jsonify({
            "is_chat": True,
            "message": (
                "Aap booking confirm kar sakte hain ya nayi location batayein."
            ),
            "logs": ai_system.logs
        })
    else:
        session.clear()
        return jsonify({
            "is_chat": True,
            "message": "Kuch masla aa gaya. Dobara likhein — kya service chahiye?",
            "logs": ai_system.logs
        })


def _do_match(user_name):
    """Runs matching agent and returns provider card or error message."""
    service   = session.get('service')
    location  = session.get('location')
    time_slot = session.get('time')

    intent = {
        "service":  service,
        "location": location,
        "time":     time_slot,
        "city":     "Sukkur"
    }

    ai_system.logs = []
    provider = ai_system.matching_agent(intent)
    

    if not provider:
        return jsonify({
            "is_chat": True,
            "message": (
                f"Afsos! Is waqt **{location or 'is ilaqe'}** mein "
                f"**{service}** provider available nahi hai. Thodi der baad try karein."
            ),
            "logs": ai_system.logs
        })

    loc_display  = location  or 'Sukkur'
    time_display = time_slot or 'ASAP'

    msg = (
        f"**Service Request:** {service}\n\n"
        f"**Location:** {loc_display}\n\n"
        f"**Time:** {time_display}\n\n"
        f"**Recommended Provider:** {provider['name']} "
        f"({provider.get('distance_km')} km away, ⭐ {provider.get('rating')})\n"
        f"*(Experience: {provider.get('experience_years', 0)} yrs | "
        f"Base Rate: Rs. {provider.get('base_rate', 'N/A')})*\n\n"
        f"**Reasoning:** Nearest available provider in {provider.get('location')}, "
        f"ranked by highest rating and experience."
    )

    return jsonify({
        "provider": provider,
        "message":  msg,
        "logs":     ai_system.logs
    })


@app.route('/book', methods=['POST'])
def book():
    try:
        data      = request.get_json(force=True, silent=True) or {}
        provider  = data.get('provider')
        user_name = data.get('user_name', 'User')

        if not provider or not provider.get('name'):
            return jsonify({"error": "Provider data missing.", "logs": []})

        ai_system.logs = []
        result = ai_system.action_agent(provider)

        if not result or result.get('error'):
            return jsonify({
                "error": result.get('error', 'Booking failed.') if result else 'Booking failed.',
                "logs":  ai_system.logs
            })

        result['logs']      = ai_system.logs
        result['user_name'] = user_name
        return jsonify(result)

    except Exception as exc:
        return jsonify({"error": f"Booking error: {exc}", "logs": ai_system.logs})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))

app.run(
    debug=False,
    host='0.0.0.0',
    port=port,
    threaded=True
)
