# AsaanRaabta AI - Antigravity Orchestrator

## Overview
**AsaanRaabta AI** is a fully autonomous, multi-agent service orchestration platform designed for the informal economy (AC Technicians, Plumbers, Electricians, Tutors, etc.). It goes beyond simple directory listings by employing a sophisticated agentic workflow to understand natural language intents, discover nearby providers, execute booking simulations, and schedule automated follow-ups.

This project was built to fulfill all requirements of the **AI Seekho Challenge 2**.

## System Architecture & Agentic Workflow
The system utilizes a structured pipeline comprising four distinct agents, all orchestrated via the `AntigravityOrchestrator` class:

1. **Intent Agent (Understanding & Planning)**
   - Processes unstructured natural language (Urdu, Roman Urdu, Sindhi, English).
   - Extracts Service Type, Location, and Time.
   - Decides if the input is a conversational query or a service request.
2. **Matching Agent (Discovery & Decision)**
   - Filters the mock dataset (`providers.json`) based on the extracted service.
   - Evaluates providers based on exact location match, proximity, and availability.
   - Outputs the highest-ranked provider with clear reasoning.
3. **Action Agent (Execution & Simulation)**
   - Performs a true state change by confirming the booking and removing the time slot from the dataset to prevent double-booking.
   - Appends the booking record to `bookings.csv` (simulated database).
   - Triggers the simulated SMS Notification API.
4. **Follow-Up Agent (Post-Execution)**
   - Automatically schedules a multi-step workflow into `followups.json` (Reminder, Status Update, Completion Confirmation).
   - Injects the booking context into the LLM's memory for seamless conversational follow-ups.

## How Google Antigravity is Used
The core orchestration of the platform is managed by the custom Antigravity framework (`AntigravityOrchestrator`). This framework acts as the central brain:
- It maintains the state of all mock databases.
- It sequentially routes data between the Intent, Matching, Action, and Follow-up agents.
- It maintains a **Traceable Log** (`self.logs`) of every decision, reasoning step, and tool usage, which is streamed directly to the frontend's dark "Agent Traces" console for full transparency.

## APIs & Tools Used
1. **Google Vertex AI (Gemini 2.5 Flash)**: Used within the Intent Agent for robust natural language understanding, entity extraction, and conversational formatting.
2. **Mock Google Maps API (`tool_google_maps_api`)**: Simulated tool call within the Matching Agent to calculate proximity and neighborhood relevance.
3. **Mock Twilio SMS API (`tool_twilio_sms_api`)**: Simulated tool call within the Action Agent to dispatch confirmation text messages.
4. **Flask (Python Backend)**: Serves the RESTful endpoints for the chat interface.
5. **Vanilla JS & Bootstrap**: Powers the responsive mobile-frame UI.

## Assumptions and Limitations
- **Mock Data**: Real-time GPS location tracking is simulated. The `providers.json` dataset acts as a static mock database for discovery.
- **LLM Fallback**: If the Gemini API rate limits or fails, the Intent Agent gracefully falls back to a deterministic NLP engine using Regular Expressions to ensure zero downtime.
- **Action Simulation**: SMS messages and Google Maps distance calculations are simulated as tool logs rather than executing live HTTP requests to third-party paid APIs, adhering to the "no real sensitive data" guideline.

## How to Run
1. Ensure you have Python installed.
2. Install dependencies: `pip install flask google-genai`
3. Run the application: `python app.py`
4. Open your browser and navigate to `http://127.0.0.1:5000`
