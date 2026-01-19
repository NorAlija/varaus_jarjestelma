from datetime import datetime, timezone  # Import datetime tools for time validation and UTC handling.
from threading import Lock  # Import Lock to make in-memory operations safe under concurrent requests.
from typing import Dict, List, Optional  # Import typing helpers for clearer type annotations.
from uuid import uuid4  # Import uuid generator for reservation IDs.

from fastapi import FastAPI, HTTPException, Path  # Import FastAPI core and HTTP error utilities.
from pydantic import BaseModel, Field, model_validator  # Import Pydantic base model and validation tools.


app = FastAPI(title="Room Booking API (In-Memory)")  # Create the FastAPI application instance.


# -----------------------------
# In-memory "database" section
# -----------------------------

ROOMS: Dict[str, str] = {  # Define exactly 6 rooms as a simple in-memory mapping of room_id -> display name.
    "aurora": "Aurora",  # Room 1.
    "borealis": "Borealis",  # Room 2.
    "helmi": "Helmi",  # Room 3.
    "sauna": "Sauna",  # Room 4.
    "sisu": "Sisu",  # Room 5.
    "taiga": "Taiga",  # Room 6.
}  # End of room definitions.

RESERVATIONS_BY_ID: Dict[str, dict] = {}  # Store reservations by reservation_id for fast cancel/delete lookups.
RESERVATION_IDS_BY_ROOM: Dict[str, List[str]] = {rid: [] for rid in ROOMS}  # Store reservation IDs per room.
DB_LOCK = Lock()  # Global lock to prevent race conditions during create/cancel operations.


# -----------------------------
# Pydantic models (request/response)
# -----------------------------

class ReservationCreateRequest(BaseModel):  # Define the expected JSON body for creating a reservation.
    user_id: str = Field(..., min_length=1, max_length=64)  # Identify the booking user (simple string ID).
    room_id: str = Field(..., min_length=1, max_length=32)  # Identify which room to book.
    start_time: datetime  # Reservation start time (ISO-8601 datetime expected).
    end_time: datetime  # Reservation end time (ISO-8601 datetime expected).

    @model_validator(mode="after")  # Run validation after the model is parsed.
    def validate_times(self) -> "ReservationCreateRequest":  # Define custom validation for time logic.
        # Ensure datetimes are timezone-aware to avoid ambiguous comparisons (security/consistency).
        if self.start_time.tzinfo is None or self.start_time.tzinfo.utcoffset(self.start_time) is None:  # Check tz awareness.
            raise ValueError("start_time must include a timezone offset (e.g. 2026-01-19T10:00:00+02:00).")  # Reject naive time.
        if self.end_time.tzinfo is None or self.end_time.tzinfo.utcoffset(self.end_time) is None:  # Check tz awareness.
            raise ValueError("end_time must include a timezone offset (e.g. 2026-01-19T11:00:00+02:00).")  # Reject naive time.

        # Enforce start < end (required business rule).
        if self.start_time >= self.end_time:  # Compare start and end.
            raise ValueError("start_time must be before end_time.")  # Reject invalid time range.

        # Enforce "not in the past" (required business rule).
        now_utc = datetime.now(timezone.utc)  # Use server-side UTC "now" to compare safely.
        start_utc = self.start_time.astimezone(timezone.utc)  # Convert start_time to UTC.
        if start_utc < now_utc:  # Check whether the reservation starts in the past.
            raise ValueError("Reservations cannot be placed in the past.")  # Reject past reservations.

        return self  # Return the validated model instance.


class ReservationResponse(BaseModel):  # Define the reservation response schema returned by the API.
    reservation_id: str  # Unique reservation identifier.
    user_id: str  # User who booked the room.
    room_id: str  # Room that was booked.
    start_time: datetime  # Start time of booking.
    end_time: datetime  # End time of booking.


class CancelResponse(BaseModel):  # Define a small response schema for cancellation results.
    cancelled: bool  # Whether cancellation succeeded.
    reservation_id: str  # Which reservation was cancelled.


# -----------------------------
# Helper functions
# -----------------------------

def overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:  # Check time overlap.
    # Overlap rule: two ranges overlap if startA < endB AND endA > startB (standard interval overlap logic).
    return a_start < b_end and a_end > b_start  # Return True if overlapping; otherwise False.


def require_room_exists(room_id: str) -> None:  # Validate room existence.
    if room_id not in ROOMS:  # If the room_id is not in our fixed set of 6 rooms.
        raise HTTPException(status_code=404, detail="Room not found.")  # Return 404 to the client.


# -----------------------------
# Routes
# -----------------------------

@app.get("/rooms")  # Define endpoint to list available rooms.
def list_rooms() -> Dict[str, str]:  # Return mapping of room_id -> room name.
    return ROOMS  # Return the fixed in-memory room list.


@app.post("/reservations", response_model=ReservationResponse, status_code=201)  # Define endpoint to create reservation.
def create_reservation(req: ReservationCreateRequest) -> ReservationResponse:  # Accept validated reservation request.
    require_room_exists(req.room_id)  # Ensure the room exists before booking.

    # Normalize times to UTC for consistent overlap checks and storage (security/consistency best practice).
    start_utc = req.start_time.astimezone(timezone.utc)  # Convert request start_time to UTC.
    end_utc = req.end_time.astimezone(timezone.utc)  # Convert request end_time to UTC.

    with DB_LOCK:  # Lock around read-check-write to prevent race conditions (double-booking under concurrency).
        # Fetch all reservation IDs for this room.
        room_res_ids = RESERVATION_IDS_BY_ROOM[req.room_id]  # Get list of reservation IDs for the room.

        # Check against existing reservations for overlap.
        for existing_id in room_res_ids:  # Iterate over each reservation in that room.
            existing = RESERVATIONS_BY_ID[existing_id]  # Fetch the stored reservation record.
            ex_start = existing["start_time"]  # Read existing start_time (stored in UTC).
            ex_end = existing["end_time"]  # Read existing end_time (stored in UTC).
            if overlaps(start_utc, end_utc, ex_start, ex_end):  # Check overlap with the new request.
                raise HTTPException(  # Raise an HTTP error to reject double-booking.
                    status_code=409,  # 409 Conflict is appropriate for resource scheduling conflicts.
                    detail="Reservation overlaps with an existing reservation for this room.",
                )  # End of HTTPException.

        # Create a new reservation ID.
        reservation_id = str(uuid4())  # Generate a random UUID for uniqueness.

        # Store the reservation record (in UTC for stable comparisons).
        record = {  # Create a dict record to store in memory.
            "reservation_id": reservation_id,  # Save reservation ID.
            "user_id": req.user_id,  # Save user ID.
            "room_id": req.room_id,  # Save room ID.
            "start_time": start_utc,  # Save start time in UTC.
            "end_time": end_utc,  # Save end time in UTC.
        }  # End record creation.

        RESERVATIONS_BY_ID[reservation_id] = record  # Insert record into global reservation map.
        RESERVATION_IDS_BY_ROOM[req.room_id].append(reservation_id)  # Add reservation ID to the room index.

    # Return response (times are UTC datetimes).
    return ReservationResponse(**record)  # Convert stored record into the declared response model.


@app.delete("/reservations/{reservation_id}", response_model=CancelResponse)  # Define endpoint to cancel a reservation.
def cancel_reservation(reservation_id: str = Path(..., min_length=1, max_length=64)) -> CancelResponse:  # Validate path.
    with DB_LOCK:  # Lock to prevent inconsistent state while deleting.
        if reservation_id not in RESERVATIONS_BY_ID:  # If reservation does not exist.
            raise HTTPException(status_code=404, detail="Reservation not found.")  # Return 404.

        record = RESERVATIONS_BY_ID.pop(reservation_id)  # Remove reservation record and keep it for room cleanup.
        room_id = record["room_id"]  # Read which room it belonged to.

        # Remove the reservation ID from the room index safely.
        room_list = RESERVATION_IDS_BY_ROOM.get(room_id, [])  # Get room list (should exist, but be defensive).
        if reservation_id in room_list:  # If the ID is present in the list.
            room_list.remove(reservation_id)  # Remove the ID to keep indexes consistent.

    return CancelResponse(cancelled=True, reservation_id=reservation_id)  # Confirm cancellation success.


@app.get("/rooms/{room_id}/reservations", response_model=List[ReservationResponse])  # Define endpoint to list room bookings.
def list_reservations_for_room(
    room_id: str = Path(..., min_length=1, max_length=32),  # Validate the room_id path parameter.
    user_id: Optional[str] = None,  # Optional query parameter to filter by user_id if desired.
) -> List[ReservationResponse]:  # Return list of reservations.
    require_room_exists(room_id)  # Ensure room exists.

    with DB_LOCK:  # Lock to read consistent state while building the list.
        res_ids = list(RESERVATION_IDS_BY_ROOM[room_id])  # Copy reservation IDs to avoid mutation during iteration.
        records = [RESERVATIONS_BY_ID[rid] for rid in res_ids]  # Fetch all reservation records for the room.

    # Optionally filter by user_id (not required, but useful and safe).
    if user_id is not None:  # If filter is provided.
        records = [r for r in records if r["user_id"] == user_id]  # Keep only records matching the user.

    # Sort reservations by start_time for nicer output.
    records.sort(key=lambda r: r["start_time"])  # Sort by UTC start_time ascending.

    return [ReservationResponse(**r) for r in records]  # Convert dict records to response models.
