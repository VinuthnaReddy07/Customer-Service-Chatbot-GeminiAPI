
import os
import sqlite3
import streamlit as st
from google import genai
from datetime import datetime

# =====================================================
# 1. PAGE CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="SupportAI",
    page_icon="🤖",
    layout="wide"
)

# =====================================================
# 2. GEMINI CONFIGURATION
# =====================================================

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-3.5-flash-lite"

if not API_KEY:
    st.error("Gemini API key not found!")
    st.stop()

client = genai.Client(api_key=API_KEY)

# =====================================================
# 3. DATABASE CONFIGURATION
# =====================================================

DB_NAME = "supportai.db"


def initialize_database():

    conn = sqlite3.connect(DB_NAME)

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (conversation_id)
            REFERENCES conversations(id)
            ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


def create_conversation():

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    now = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO conversations
        (title, created_at, updated_at)
        VALUES (?, ?, ?)
    """, ("New Conversation", now, now))

    conversation_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return conversation_id


def get_conversations():

    conn = sqlite3.connect(DB_NAME)

    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, updated_at
        FROM conversations
        ORDER BY updated_at DESC
    """)

    conversations = cursor.fetchall()

    conn.close()

    return conversations


def save_message(conversation_id, role, content):

    conn = sqlite3.connect(DB_NAME)

    cursor = conn.cursor()

    now = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO messages
        (conversation_id, role, content, created_at)
        VALUES (?, ?, ?, ?)
    """, (conversation_id, role, content, now))

    # Update conversation timestamp
    cursor.execute("""
        UPDATE conversations
        SET updated_at = ?
        WHERE id = ?
    """, (now, conversation_id))

    # Set conversation title from first customer message
    if role == "user":

        cursor.execute("""
            SELECT COUNT(*)
            FROM messages
            WHERE conversation_id = ?
            AND role = 'user'
        """, (conversation_id,))

        count = cursor.fetchone()[0]

        if count == 1:

            title = content[:45]

            cursor.execute("""
                UPDATE conversations
                SET title = ?
                WHERE id = ?
            """, (title, conversation_id))

    conn.commit()
    conn.close()


def get_messages(conversation_id):

    conn = sqlite3.connect(DB_NAME)

    cursor = conn.cursor()

    cursor.execute("""
        SELECT role, content
        FROM messages
        WHERE conversation_id = ?
        ORDER BY id ASC
    """, (conversation_id,))

    messages = cursor.fetchall()

    conn.close()

    return [
        {"role": role, "content": content}
        for role, content in messages
    ]


def delete_conversation(conversation_id):

    conn = sqlite3.connect(DB_NAME)

    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM messages
        WHERE conversation_id = ?
    """, (conversation_id,))

    cursor.execute("""
        DELETE FROM conversations
        WHERE id = ?
    """, (conversation_id,))

    conn.commit()
    conn.close()


# Initialize database
initialize_database()

# =====================================================
# 4. SYSTEM PROMPT
# =====================================================

SYSTEM_PROMPT = """
You are SupportAI, a professional customer service assistant.

Your responsibilities:

1. Greet customers politely.
2. Understand customer problems.
3. Provide clear solutions.
4. Give step-by-step troubleshooting.
5. Ask relevant follow-up questions.
6. Maintain conversation context.
7. Be friendly and professional.

Support categories:

- Orders and Delivery
- Payments and Billing
- Returns and Refunds
- Product Information
- Account Assistance
- Technical Support

Important rules:

- Never invent order details.
- Never invent company policies.
- Never claim that a refund was processed.
- Never request passwords or OTPs.
- If information is unavailable, explain that
  human support may be required.
"""

# =====================================================
# 5. CUSTOM CSS
# =====================================================

st.markdown("""
<style>

.stApp {
    background: linear-gradient(135deg, #090e1a, #111827);
    color: white;
}

.block-container {
    max-width: 1150px;
    padding-top: 2rem;
}

.hero {
    background: linear-gradient(120deg, #172554, #312e81);
    padding: 28px;
    border-radius: 20px;
    text-align: center;
    margin-bottom: 25px;
}

.hero h1 {
    color: white;
    font-size: 38px;
}

.hero p {
    color: #cbd5e1;
}

[data-testid="stSidebar"] {
    background: #0f172a;
}

[data-testid="stChatMessage"] {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 15px;
    padding: 15px;
    animation: fadeIn 0.4s ease-in-out;
}

@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.stButton button {
    border-radius: 10px;
    border: 1px solid #6366f1;
}

</style>
""", unsafe_allow_html=True)

# =====================================================
# 6. SESSION STATE
# =====================================================

if "active_conversation_id" not in st.session_state:

    conversations = get_conversations()

    if conversations:
        st.session_state.active_conversation_id = conversations[0][0]
    else:
        st.session_state.active_conversation_id = create_conversation()

# =====================================================
# 7. SIDEBAR
# =====================================================

with st.sidebar:

    st.title("🤖 SupportAI")

    st.caption("Intelligent Customer Support")

    st.divider()

    # New conversation
    if st.button("➕ New Conversation", use_container_width=True):

        new_id = create_conversation()

        st.session_state.active_conversation_id = new_id

        st.rerun()

    st.divider()

    st.markdown("### 🕘 Previous Conversations")

    conversations = get_conversations()

    if conversations:

        conversation_titles = {
            item[0]: item[1]
            for item in conversations
        }

        conversation_ids = [
            item[0] for item in conversations
        ]

        active_id = st.session_state.active_conversation_id

        if active_id not in conversation_ids:
            active_id = conversation_ids[0]

        selected_id = st.selectbox(
            "Open conversation",
            options=conversation_ids,
            index=conversation_ids.index(active_id),
            format_func=lambda x: conversation_titles[x],
            label_visibility="collapsed"
        )

        st.session_state.active_conversation_id = selected_id

        if st.button("🗑️ Delete Current Conversation",
                     use_container_width=True):

            delete_conversation(selected_id)

            remaining = get_conversations()

            if remaining:
                st.session_state.active_conversation_id = remaining[0][0]
            else:
                st.session_state.active_conversation_id = create_conversation()

            st.rerun()

    st.divider()

    st.markdown("### Support Categories")

    st.write("📦 Orders & Delivery")
    st.write("💳 Payments & Billing")
    st.write("🔄 Returns & Refunds")
    st.write("🛍️ Product Information")
    st.write("👤 Account Assistance")
    st.write("🛠️ Technical Support")

    st.divider()

    st.markdown("### Technology")

    st.write("🧠 Gemini API")
    st.write("🐍 Python")
    st.write("🎨 Streamlit")
    st.write("🗄️ SQLite")

# =====================================================
# 8. MAIN HEADER
# =====================================================

st.markdown("""
<div class="hero">

    <h1>🤖 SupportAI</h1>

    <p>Your Intelligent Customer Service Assistant</p>

    <p>Ask questions. Get solutions. Smarter support.</p>

</div>
""", unsafe_allow_html=True)

# =====================================================
# 9. LOAD SELECTED CONVERSATION
# =====================================================

conversation_id = st.session_state.active_conversation_id

messages = get_messages(conversation_id)

if not messages:

    st.markdown("### 👋 Hello! How can I help you today?")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info("📦 Order & Delivery")

    with col2:
        st.info("💳 Payments & Billing")

    with col3:
        st.info("🔄 Returns & Refunds")

# =====================================================
# 10. DISPLAY PREVIOUS MESSAGES
# =====================================================

for message in messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])

# =====================================================
# 11. CUSTOMER INPUT
# =====================================================

user_input = st.chat_input("Type your question here...")

if user_input:

    # Save customer message in SQLite
    save_message(
        conversation_id,
        "user",
        user_input
    )

    with st.chat_message("user"):
        st.markdown(user_input)

    # Reload complete conversation history
    messages = get_messages(conversation_id)

    conversation = "\n\n".join([
        f"{'Customer' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
        for m in messages
    ])

    # =================================================
    # 12. GEMINI API
    # =================================================

    with st.chat_message("assistant"):

        try:

            with st.spinner("🤖 SupportAI is thinking..."):

                response = client.models.generate_content(
                    model=MODEL,
                    contents=conversation,
                    config={
                        "system_instruction": SYSTEM_PROMPT,
                        "temperature": 0.5,
                        "max_output_tokens": 800
                    }
                )

                answer = response.text

                if not answer:
                    answer = "Sorry, I couldn't generate a response."

            st.markdown(answer)

            # Save AI response in SQLite
            save_message(
                conversation_id,
                "assistant",
                answer
            )

        except Exception as e:

            st.error(
                "Sorry, the AI service is temporarily unavailable."
            )

            st.caption(f"Technical details: {e}")

