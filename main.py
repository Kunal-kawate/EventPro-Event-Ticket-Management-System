import streamlit as st
import sqlite3
import hashlib
import pandas as pd

# --- DATABASE SETUP ---

# Function to connect to the SQLite database
def get_db_connection():
    conn = sqlite3.connect('ticketManage.db')
    conn.row_factory = sqlite3.Row
    return conn

# Function to create tables if they don't exist
def create_tables():
    conn = get_db_connection()
    c = conn.cursor()
    # Admin table
    c.execute('''
        CREATE TABLE IF NOT EXISTS AdminData (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    ''')
    # Event table
    c.execute('''
        CREATE TABLE IF NOT EXISTS EventData (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            venue TEXT NOT NULL,
            description TEXT
        )
    ''')
    # Ticket booking table
    c.execute('''
        CREATE TABLE IF NOT EXISTS TicketBookData (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name TEXT NOT NULL,
            user_name TEXT NOT NULL,
            user_phone TEXT NOT NULL,
            FOREIGN KEY (event_name) REFERENCES EventData (name)
        )
    ''')
    conn.commit()
    conn.close()

# --- HELPER FUNCTIONS ---

# Function to hash passwords
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# Function to check hashed passwords
def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

# --- ADMIN FUNCTIONS ---

def add_admin(username, password):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO AdminData (username, password) VALUES (?, ?)', (username, make_hashes(password)))
        conn.commit()
        st.success("Admin account created successfully!")
    except sqlite3.IntegrityError:
        st.warning("Username already exists.")
    finally:
        conn.close()

def login_admin(username, password):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT password FROM AdminData WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    if data:
        return check_hashes(password, data['password'])
    return False

# --- EVENT FUNCTIONS ---

def get_bookings_for_event(event_name):
    conn = get_db_connection()
    bookings = conn.execute('SELECT user_name, user_phone FROM TicketBookData WHERE event_name = ?', (event_name,)).fetchall()
    conn.close()
    return bookings

def add_event(name, date, time, venue, description):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO EventData (name, date, time, venue, description) VALUES (?, ?, ?, ?, ?)',
                  (name, date, time, venue, description))
        conn.commit()
        st.success(f"Event '{name}' added successfully!")
    except sqlite3.IntegrityError:
        st.error(f"Error: An event with the name '{name}' already exists.")
    finally:
        conn.close()

def get_all_events():
    conn = get_db_connection()
    events = conn.execute('SELECT * FROM EventData ORDER BY date, time').fetchall()
    conn.close()
    return events

def delete_event(event_name):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM EventData WHERE name = ?', (event_name,))
    # Also delete associated ticket bookings to maintain data integrity
    c.execute('DELETE FROM TicketBookData WHERE event_name = ?', (event_name,))
    conn.commit()
    conn.close()
    st.success(f"Event '{event_name}' and all its bookings have been deleted.")

def get_booking_count(event_name):
    conn = get_db_connection()
    count = conn.execute('SELECT COUNT(*) FROM TicketBookData WHERE event_name = ?', (event_name,)).fetchone()[0]
    conn.close()
    return count

# --- TICKET BOOKING FUNCTIONS ---

def book_ticket(event_name, user_name, user_phone):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO TicketBookData (event_name, user_name, user_phone) VALUES (?, ?, ?)',
              (event_name, user_name, user_phone))
    conn.commit()
    conn.close()
    st.success(f"Ticket booked for {user_name} for the event '{event_name}'!")

# --- STREAMLIT UI ---

st.set_page_config(page_title="EventPro", layout="wide")



def admin_page():
    st.title("Admin Panel")

    if 'admin_logged_in' not in st.session_state:
        st.session_state.admin_logged_in = False

    if not st.session_state.admin_logged_in:
        choice = st.selectbox("Login / Sign Up", ["Login", "Sign Up"])

        if choice == "Login":
            st.subheader("Admin Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type='password')
            if st.button("Login"):
                if login_admin(username, password):
                    st.session_state.admin_logged_in = True
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error("Incorrect username or password.")
        else:
            st.subheader("Create New Admin Account")
            new_username = st.text_input("Choose a Username")
            new_password = st.text_input("Choose a Password", type='password')
            if st.button("Sign Up"):
                if new_username and new_password:
                    add_admin(new_username, new_password)
                else:
                    st.warning("Please enter both username and password.")

    else:
        st.success("You are logged in as an Admin.")
        
        st.header("Admin Dashboard")

        # --- Add Event Section ---
        with st.expander("➕ Add New Event"):
            with st.form("add_event_form", clear_on_submit=True):
                event_name = st.text_input("Event Name")
                col1, col2 = st.columns(2)
                with col1:
                    event_date = st.date_input("Event Date")
                with col2:
                    event_time = st.time_input("Event Time")
                event_venue = st.text_input("Venue")
                event_description = st.text_area("Description")
                
                submitted = st.form_submit_button("Add Event")
                if submitted:
                    if event_name and event_date and event_time and event_venue:
                        add_event(event_name, str(event_date), str(event_time), event_venue, event_description)
                    else:
                        st.warning("Please fill in all required fields: Name, Date, Time, and Venue.")

        st.markdown("---")
        
        # --- Manage Events Section ---
        st.header("📊 Manage Events")
        all_events = get_all_events()
        if not all_events:
            st.info("No events have been added yet.")
        else:
            event_names = [event['name'] for event in all_events]
            
            # Display event data and booking counts
            event_data = []
            for event in all_events:
                count = get_booking_count(event['name'])
                event_data.append({
                    "Event Name": event['name'],
                    "Date": event['date'],
                    "Time": event['time'],
                    "Venue": event['venue'],
                    "Tickets Booked": count
                })
            
            st.table(pd.DataFrame(event_data))

            # Delete event
            st.subheader("🗑️ Delete an Event")
            event_to_delete = st.selectbox("Select Event to Delete", options=event_names)
            if st.button("Delete Event", key=f"delete_{event_to_delete}"):
                delete_event(event_to_delete)
                st.rerun()
            
            # --- NEW FEATURE: View Bookings ---
            st.markdown("---")
            st.subheader("🎟️ View Ticket Bookings")
            if event_names:
                event_to_view = st.selectbox("Select an Event to see Bookings", options=event_names, key="view_bookings")
                
                if event_to_view:
                    bookings = get_bookings_for_event(event_to_view)
                    if bookings:
                        # Convert list of Row objects to a DataFrame for better display
                        booking_df = pd.DataFrame(bookings, columns=["Booked By (Name)", "Phone Number"])
                        st.dataframe(booking_df)
                    else:
                        st.info(f"No tickets have been booked for '{event_to_view}' yet.")

        if st.button("Logout"):
            st.session_state.admin_logged_in = False
            st.rerun()


def events_page():
    st.title("🎉 Upcoming Events")
    st.markdown("Browse our events and book your tickets now!")
    
    all_events = get_all_events()

    if not all_events:
        st.info("There are no upcoming events at the moment. Please check back later!")
        return

    # Create a card-like interface using columns
    cols = st.columns(3)
    for i, event in enumerate(all_events):
        with cols[i % 3]:
            with st.container():
                st.subheader(event['name'])
                st.markdown(f"**📍 Venue:** {event['venue']}")
                st.markdown(f"**📅 Date:** {event['date']}")
                st.markdown(f"**⏰ Time:** {event['time']}")
                if event['description']:
                    st.markdown(f"**📝 About:** {event['description']}")
                
                # Booking Form inside an expander
                with st.expander("Book Your Ticket"):
                    with st.form(key=f"book_form_{event['id']}", clear_on_submit=True):
                        user_name = st.text_input("Your Name", key=f"name_{event['id']}")
                        user_phone = st.text_input("Your Phone Number", key=f"phone_{event['id']}")
                        
                        book_button = st.form_submit_button(label="Confirm Booking")
                        
                        if book_button:
                            if user_name and user_phone:
                                book_ticket(event['name'], user_name, user_phone)
                            else:
                                st.warning("Please enter your name and phone number.")
            st.markdown("---")


def main():
    # Run this function at the start of the app to create the DB and tables
    create_tables()

    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Events", "Admin"])

    if page == "Admin":
        admin_page()
    else:
        events_page()

if __name__ == '__main__':
    main()