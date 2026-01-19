
# Room Booking API (FastAPI, In-Memory)

This project is a **room booking REST API** built with **FastAPI**.
It allows users to create, list, and cancel room reservations while enforcing
time-based and concurrency constraints.

The application uses an **in-memory data store** and is intended for learning,
prototyping, and technical evaluation purposes.

---

## Features

* Book a room for a specific time period
* Cancel an existing reservation
* List reservations for a specific room
* Optional filtering of reservations by user
* Prevents overlapping reservations for the same room
* Prevents reservations in the past
* Restricts reservations to the **current calendar year**
* Thread-safe booking and cancellation logic
* Timezone-aware datetime handling

---

## Room Configuration

The system contains **exactly six rooms**, defined in memory:

* `aurora`
* `borealis`
* `helmi`
* `sauna`
* `sisu`
* `taiga`

Room identifiers are fixed and validated on every request.

---

## Timezone Handling

* All datetime values **must include a timezone offset**
  (e.g. `2026-06-10T10:00:00+02:00`)
* This allows reservations to be made from **different countries**
* Internally, all times are normalized to **UTC** for consistency
* Calendar-based rules (such as year restrictions) are enforced consistently

---

## Business Rules

### Reservation Rules

* `start_time` must be **before** `end_time`
* Reservations **cannot start in the past**
* Reservations must be within the **current calendar year**
* Reservations **cannot span across years**
* Two reservations for the same room **cannot overlap**
* Back-to-back reservations are allowed

### Cancellation Rules

* Cancelling a non-existent reservation returns **404**
* Cancellation is **not idempotent**

---

## Tech Stack

* Python 3.10+
* FastAPI
* Pydantic (data validation)
* Uvicorn (ASGI server)

---

## Installation & Setup

### Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install dependencies

```bash
pip install fastapi uvicorn
```

---

## Running the Application

```bash
uvicorn main:app --reload
```

The API will be available at:

```
http://127.0.0.1:8000
```

Interactive API documentation:

* Swagger UI: `http://127.0.0.1:8000/docs`
* OpenAPI spec: `http://127.0.0.1:8000/openapi.json`

---

## API Endpoints

### List Available Rooms

```http
GET /rooms
```

---

### Create a Reservation

```http
POST /reservations
```

**Request body example:**

```json
{
  "user_id": "user123",
  "room_id": "aurora",
  "start_time": "2026-06-10T10:00:00+02:00",
  "end_time": "2026-06-10T11:00:00+02:00"
}
```

**Responses:**

* `201 Created` – reservation created
* `404 Not Found` – invalid room
* `409 Conflict` – overlapping reservation
* `422 Unprocessable Entity` – invalid time rules

---

### Cancel a Reservation

```http
DELETE /reservations/{reservation_id}
```

**Responses:**

* `200 OK` – reservation cancelled
* `404 Not Found` – reservation does not exist

---

### List Reservations for a Room

```http
GET /rooms/{room_id}/reservations
```

Optional query parameter:

```http
?user_id=user123
```

**Responses:**

* `200 OK` – list of reservations
* `404 Not Found` – invalid room

---

## Concurrency & Safety

* All booking and cancellation operations are protected by a **thread lock**
* Prevents race conditions and double bookings under concurrent requests
* Reservation IDs are generated using UUIDs to prevent enumeration attacks

---

## Limitations

* Data is stored **in memory** (lost on restart)
* No authentication or authorization
* No persistence layer or database
* Intended for learning and demonstration purposes only

---

