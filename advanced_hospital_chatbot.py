import streamlit as st
import sqlite3
import datetime
import re
import spacy

# Load NLP model
nlp = spacy.load("en_core_web_sm")

# ----- Database Setup -----
conn = sqlite3.connect('hospital.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS doctors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    department TEXT,
    available_days TEXT,
    available_time TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_name TEXT,
    doctor_name TEXT,
    date TEXT,
    time TEXT
)
''')

# Sample doctors
cursor.execute("SELECT COUNT(*) FROM doctors")
if cursor.fetchone()[0] == 0:
    cursor.executemany("INSERT INTO doctors (name, department, available_days, available_time) VALUES (?, ?, ?, ?)", [
        ("Dr. Riya Sharma", "cardiologist", "Mon,Wed,Fri", "10am-2pm"),
        ("Dr. Arjun Mehta", "dermatologist", "Tue,Thu,Sat", "11am-3pm"),
        ("Dr. Neha Rao", "neurologist", "Mon,Fri", "9am-1pm")
    ])
    conn.commit()

# ----- Intent Detection -----
def detect_intent(text):
    text = text.lower()
    if any(word in text for word in ["book", "appointment", "schedule"]):
        return "BookAppointment"
    elif any(word in text for word in ["cancel", "remove"]):
        return "CancelAppointment"
    elif any(word in text for word in ["doctor", "available", "specialist"]):
        return "DoctorInfo"
    elif any(word in text for word in ["hi", "hello", "hey"]):
        return "Greet"
    elif any(word in text for word in ["bye", "exit", "thanks"]):
        return "Exit"
    else:
        return "Unknown"

# ----- Entity Extraction -----
def extract_entities(text):
    doc = nlp(text)
    entities = {"doctor": None, "date": None, "time": None}

    # Extract doctor/specialization
    for token in doc:
        if token.text.lower() in ["cardiologist", "dermatologist", "neurologist"]:
            entities["doctor"] = token.text.lower()

    # Extract date/time
    date_match = re.search(r'\d{4}-\d{2}-\d{2}', text)
    if date_match:
        entities["date"] = date_match.group()
    elif "tomorrow" in text:
        entities["date"] = str(datetime.date.today() + datetime.timedelta(days=1))
    elif "today" in text:
        entities["date"] = str(datetime.date.today())

    time_match = re.search(r'\d{1,2}(am|pm)', text)
    if time_match:
        entities["time"] = time_match.group()

    return entities

# ----- Chatbot Response Logic -----
def get_response(user_input, patient_name="Patient"):
    intent = detect_intent(user_input)
    entities = extract_entities(user_input)

    if intent == "Greet":
        return f"Hello {patient_name}! 👋 How can I assist you today?"

    elif intent == "BookAppointment":
        if not entities["doctor"]:
            return "Sure! Which specialist would you like to book (e.g., cardiologist, dermatologist)?"
        if not entities["date"]:
            return "Please provide the appointment date (YYYY-MM-DD or say 'tomorrow')."

        # Fetch doctor
        cursor.execute("SELECT name FROM doctors WHERE department=?", (entities["doctor"],))
        doc = cursor.fetchone()
        if doc:
            cursor.execute("INSERT INTO appointments (patient_name, doctor_name, date, time) VALUES (?, ?, ?, ?)",
                           (patient_name, doc[0], entities["date"], entities["time"] or "11am"))
            conn.commit()
            return f"✅ Appointment booked with {doc[0]} ({entities['doctor'].title()}) on {entities['date']} at {entities['time'] or '11am'}."
        else:
            return "Sorry, no such specialist found."

    elif intent == "CancelAppointment":
        cursor.execute("SELECT * FROM appointments WHERE patient_name=?", (patient_name,))
        appt = cursor.fetchone()
        if appt:
            cursor.execute("DELETE FROM appointments WHERE id=?", (appt[0],))
            conn.commit()
            return f"❌ Appointment with {appt[2]} on {appt[3]} has been cancelled."
        else:
            return "You don’t have any active appointments."

    elif intent == "DoctorInfo":
        cursor.execute("SELECT name, department, available_days, available_time FROM doctors")
        docs = cursor.fetchall()
        info = "\n".join([f"{d[0]} - {d[1].title()} ({d[2]}, {d[3]})" for d in docs])
        return f"Here are our available doctors:\n{info}"

    elif intent == "Exit":
        return "Goodbye! Take care 😊"

    else:
        return "Sorry, I didn’t quite understand. Could you rephrase that?"

# ----- Streamlit Chat UI -----
st.title("🏥 AI-Powered Hospital Chatbot (Advanced Version)")
st.markdown("💬 Chat with the hospital assistant below:")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

user_input = st.text_input("You:", key="input")

if st.button("Send"):
    response = get_response(user_input)
    st.session_state.chat_history.append(("You", user_input))
    st.session_state.chat_history.append(("Bot", response))

# Display chat history
for sender, msg in st.session_state.chat_history:
    if sender == "You":
        st.markdown(f"🧑‍💬 **{sender}:** {msg}")
    else:
        st.markdown(f"🤖 **{sender}:** {msg}")
