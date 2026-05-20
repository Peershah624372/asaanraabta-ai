# 🎥 AsaanRaabta AI - Demo Video Script (3-5 Minutes)

This script is designed to help you record your final demo video and score maximum points across all 6 Evaluation Criteria. 

## Preparation
1. Open your code editor showing `orchestrator.py` and `providers.json`.
2. Run the app (`python app.py`) and open `http://127.0.0.1:5000` in your browser.
3. Start your screen recording software.

---

## 🎬 Section 1: Introduction (0:00 - 0:30)
**Action:** Show the beautiful mobile UI in the browser.
**Script:** 
"Hello! Welcome to AsaanRaabta AI. This is a fully autonomous, multi-agent orchestration platform designed to help people in the informal economy seamlessly book AC Technicians, Plumbers, and Electricians. 
As per the guidelines, this is **not** a simple directory app. It is an agentic workflow powered by Google Antigravity and Vertex AI that understands intent, simulates decisions, and executes actions."

## 🎬 Section 2: Intent Understanding & Reasoning (0:30 - 1:30)
**Action:** Type `Mujhe kal subah G-13 mein AC technician chahiye` into the chat and hit send. 
*Point to the dark "Agent Traces" box at the top of the screen as the text appears.*
**Script:** 
"Watch the top console as I send my request in Roman Urdu. You are seeing the real-time reasoning logs. 
First, our **Intent Agent** processes the natural language, successfully extracting the service (AC Technician), the location (G-13), and calculating 'kal subah' as the 10:00 AM time block.
Next, our **Matching Agent** triggers. It searches our mock dataset and uses a simulated Google Maps tool to calculate proximity. It finds 'Islamabad G-13 AC Services' just 2.1km away and selects it based on distance and a high 4.8 rating."

## 🎬 Section 3: Action Execution & State Change (1:30 - 2:30)
**Action:** Show the result card in the chat. Click the **"Confirm Booking"** button. Wait for the Digital Receipt to appear.
**Script:**
"The Orchestrator explains its decision clearly to the user. Now, I will click Confirm Booking to trigger the **Action Agent**. 
Notice the agent traces again. The Action Agent executes a true state change. It removes the 10:00 AM slot from our database so no one else can book it, simulating a real backend operation. It then generates this Digital Service Receipt and triggers a mock Twilio SMS API."

## 🎬 Section 4: Follow-up Automation & The Database (2:30 - 3:30)
**Action:** Open your code editor. Show the `bookings.csv` file, then show the `followups.json` file.
**Script:**
"To prove this isn't just frontend magic, let's look at the backend. 
Here is our `bookings.csv` spreadsheet. You can see the booking was explicitly logged here, satisfying the database requirement. 
Furthermore, our **Follow-Up Agent** automatically generated this `followups.json` file. It simulated scheduling three future events: a reminder 1 hour before, a status update at the time of appointment, and a completion confirmation ping afterward. This demonstrates true end-to-end agentic workflow."

## 🎬 Section 5: Architecture & Conclusion (3:30 - 4:00)
**Action:** Show `orchestrator.py`, specifically the `process_request` function routing the agents.
**Script:**
"All of this was powered by our custom Antigravity Orchestrator pipeline, which routes data sequentially through planning, decision, action, and follow-up phases. 
Thank you for watching the AsaanRaabta AI demo!"
