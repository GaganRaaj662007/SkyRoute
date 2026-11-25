from flask import Flask, render_template, request, redirect, url_for
from datetime import date
import sqlite3
import uuid
import re

app = Flask(__name__)
def init_db():
    conn = sqlite3.connect("skyroute.db")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id TEXT UNIQUE NOT NULL,
            flight_id INTEGER NOT NULL,
            airline TEXT NOT NULL,
            source TEXT NOT NULL,
            destination TEXT NOT NULL,
            travel_date TEXT NOT NULL,
            passengers INTEGER NOT NULL,
            passenger_names TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            total_fare INTEGER NOT NULL,
            status TEXT DEFAULT 'Confirmed'
        )
    """)

    conn.commit()
    conn.close()

init_db()


# Sample flight data
flights = [
    {
        "id": 101,
        "airline": "IndiGo",
        "source": "Bengaluru",
        "destination": "Delhi",
        "departure": "08:30 AM",
        "arrival": "11:15 AM",
        "price": 4500
    },
    {
        "id": 102,
        "airline": "Air India",
        "source": "Bengaluru",
        "destination": "Delhi",
        "departure": "02:00 PM",
        "arrival": "04:45 PM",
        "price": 5200
    },
    {
        "id": 103,
        "airline": "IndiGo",
        "source": "Bengaluru",
        "destination": "Mumbai",
        "departure": "10:00 AM",
        "arrival": "11:40 AM",
        "price": 3500
    },
    {
        "id": 104,
        "airline": "Air India",
        "source": "Delhi",
        "destination": "Bengaluru",
        "departure": "09:00 AM",
        "arrival": "11:50 AM",
        "price": 4800
    },
    {
        "id": 105,
        "airline": "IndiGo",
        "source": "Chennai",
        "destination": "Hyderabad",
        "departure": "06:30 AM",
        "arrival": "07:45 AM",
        "price": 2800
    }
]

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    source = request.form.get("source")
    destination = request.form.get("destination")
    travel_date = request.form.get("date")
    passengers = request.form.get("passengers", type=int)

    if not source or not destination:
        return "Please select both cities.", 400

    if source == destination:
        return "Departure and destination cannot be the same.", 400

    try:
        selected_date = date.fromisoformat(travel_date)
    except (ValueError, TypeError):
        return "Invalid travel date.", 400

    if selected_date < date.today():
        return "Please select a future or current date.", 400

    if passengers is None or not 1 <= passengers <= 6:
        return "Select between 1 and 6 passengers.", 400

    results = []

    for flight in flights:
        if (flight["source"] == source and
                flight["destination"] == destination):
            results.append(flight)

    return render_template(
        "results.html",
        flights=results,
        source=source,
        destination=destination,
        date=travel_date,
        passengers=passengers
    )

@app.route("/book/<int:flight_id>")
def book(flight_id):

    flight = next(
        (f for f in flights if f["id"] == flight_id),
        None
    )

    if flight is None:
        return "Flight not found.", 404

    travel_date = request.args.get("date")
    passengers = request.args.get("passengers", type=int)

    if passengers is None or not 1 <= passengers <= 6:
        return "Invalid passenger count.", 400

    try:
        selected_date = date.fromisoformat(travel_date)
    except (ValueError, TypeError):
        return "Invalid travel date.", 400

    if selected_date < date.today():
        return "Invalid departure date.", 400

    return render_template(
        "booking.html",
        flight=flight,
        date=travel_date,
        passengers=passengers
    )

@app.route("/confirm", methods=["POST"])
def confirm():

    flight_id = request.form.get("flight_id", type=int)
    travel_date = request.form.get("date")
    passengers = request.form.get("passengers", type=int)

    names = [
        name.strip()
        for name in request.form.getlist("passenger_name")
    ]

    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()

    flight = next(
        (f for f in flights if f["id"] == flight_id),
        None
    )

    if flight is None:
        return "Flight not found.", 404

    if passengers is None or not 1 <= passengers <= 6:
        return "Invalid passenger count.", 400

    try:
        selected_date = date.fromisoformat(travel_date)
    except (ValueError, TypeError):
        return "Invalid travel date.", 400

    if selected_date < date.today():
        return "Invalid departure date.", 400

    if len(names) != passengers:
        return "Incorrect passenger details.", 400

    if any(not name or len(name) > 100 for name in names):
        return "Invalid passenger name.", 400

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return "Invalid email address.", 400

    if not re.fullmatch(r"[0-9]{10}", phone):
        return "Invalid phone number.", 400

    booking_id = "SR-" + uuid.uuid4().hex[:12].upper()
    total_fare = flight["price"] * passengers

    conn = sqlite3.connect("skyroute.db")

    conn.execute("""
        INSERT INTO bookings (
            booking_id, flight_id, airline,
            source, destination, travel_date,
            passengers, passenger_names,
            email, phone, total_fare, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        booking_id,
        flight_id,
        flight["airline"],
        flight["source"],
        flight["destination"],
        travel_date,
        passengers,
        ", ".join(names),
        email,
        phone,
        total_fare,
        "Confirmed"
    ))

    conn.commit()
    conn.close()

    return render_template(
        "confirmation.html",
        booking_id=booking_id,
        flight=flight,
        date=travel_date,
        passengers=passengers,
        names=names,
        total_fare=total_fare
    )

@app.route("/bookings")
def bookings():

    conn = sqlite3.connect("skyroute.db")
    conn.row_factory = sqlite3.Row

    records = conn.execute("""
        SELECT * FROM bookings
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "bookings.html",
        bookings=records
    )

@app.route("/cancel/<booking_id>", methods=["POST"])
def cancel_booking(booking_id):

    conn = sqlite3.connect("skyroute.db")

    result = conn.execute("""
        UPDATE bookings
        SET status = 'Cancelled'
        WHERE booking_id = ?
        AND status = 'Confirmed'
    """, (booking_id,))

    updated = result.rowcount

    conn.commit()
    conn.close()

    if updated == 0:
        return "Booking not found or already cancelled.", 400

    return redirect(url_for("bookings"))


if __name__ == "__main__":
    app.run(debug=True)
