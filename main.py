# Necessary modules imported
from datetime import datetime, timezone
from threading import Lock  
from typing import Dict, List, Optional  
from uuid import uuid4  
from fastapi import FastAPI, HTTPException, Path 
from pydantic import BaseModel, Field, model_validator  

app = FastAPI(title="Room Booking API (In-Memory)")  # Create the FastAPI application instance.


# -----------------------------
# In-memory "database" section: Define exactly 6 rooms as a simple in-memory mapping of room_id -> display name.
# -----------------------------

ROOMS: Dict[str, str] = {  
    "aurora": "Aurora",  
    "borealis": "Borealis", 
    "helmi": "Helmi", 
    "sauna": "Sauna", 
    "sisu": "Sisu",  
    "taiga": "Taiga",  
}  

#Store reservations
RESERVATIONS_BY_ID: Dict[str, dict] = {}  
RESERVATION_IDS_BY_ROOM: Dict[str, List[str]] = {rid: [] for rid in ROOMS} 

# Global lock to prevent race conditions during create/cancel operations.
DB_LOCK = Lock() 


# -----------------------------
# Pydantic models (request/response)
# -----------------------------

class ReservationCreateRequest(BaseModel):
    """
    Request body for creating a room reservation.
    
    Fields:
    - user_id: Identify the user
    - room_id: Identify which room to book
    - start_time: Reservation start time
    - end_time:  Reservation end time

    """
    user_id: str = Field(..., min_length=1, max_length=64) 
    room_id: str = Field(..., min_length=1, max_length=32)  
    start_time: datetime  
    end_time: datetime  

    @model_validator(mode="after")  # Run validation after the model is parsed.
    def validate_times(self) -> "ReservationCreateRequest":  # Define custom validation for time logic.
        """
        Ensures that:
        - start_time and end_time are timezone-aware
        - start_time is strictly before end_time
        - the reservation does not start in the past (UTC-based comparison)

        Raises:
            ValueError: If any temporal validation rule is violated.
        """
        
        if self.start_time.tzinfo is None or self.start_time.tzinfo.utcoffset(self.start_time) is None:
            raise ValueError("start_time must include a timezone offset (e.g. 2026-01-19T10:00:00+02:00).")
        if self.end_time.tzinfo is None or self.end_time.tzinfo.utcoffset(self.end_time) is None:
            raise ValueError("end_time must include a timezone offset (e.g. 2026-01-19T11:00:00+02:00).")

        if self.start_time >= self.end_time: 
            raise ValueError("start_time must be before end_time.") 

        
        now_utc = datetime.now(timezone.utc)  
        start_utc = self.start_time.astimezone(timezone.utc)  
        if start_utc < now_utc:  
            raise ValueError("Reservations cannot be placed in the past.")  

        return self 


class ReservationResponse(BaseModel):
    """
    Response model represanting a room reservation

    Returned after successfully creating a reservation and when
    listing reservations for a room.
    """
    reservation_id: str  
    user_id: str  
    room_id: str  
    start_time: datetime  
    end_time: datetime  


class CancelResponse(BaseModel):
    """
    Response model returned after cancelling a reservation.
    """  
    cancelled: bool  
    reservation_id: str  


# -----------------------------
# Helper functions
# -----------------------------

def overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool: 
    """
    Check time overlap.
    Return True if overlapping: otherwise False
    """
    return a_start < b_end and a_end > b_start  


def require_room_exists(room_id: str) -> None:  
    """
    Check if the room exists
    If not return 404 to the user
    """
    if room_id not in ROOMS: 
        raise HTTPException(status_code=404, detail="Room not found.")  


# -----------------------------
# Routes
# -----------------------------

@app.get("/rooms")
def list_rooms() -> Dict[str, str]:  
    """
    Endpoint to list available rooms
    """
    return ROOMS  


@app.post("/reservations", response_model=ReservationResponse, status_code=201)  # Define endpoint to create reservation.
def create_reservation(req: ReservationCreateRequest) -> ReservationResponse:  # Accept validated reservation request.
    """
    Create a new reservation for a room.

    This endpoint:
    - Validates that the requested room exists
    - Prevents overlapping reservations for the same room
    - Rejects reservations that start in the past
    - Stores all reservation times in UTC for consistency

    A unique reservation ID is generated and returned on success.

    Raises:
        HTTPException(404): If the specified room does not exist
        HTTPException(409): If the reservation overlaps with an existing one
    """
    require_room_exists(req.room_id) 

    # Normalize times to UTC for consistent overlap checks and storage (security/consistency best practice).
    start_utc = req.start_time.astimezone(timezone.utc)  
    end_utc = req.end_time.astimezone(timezone.utc)  

    with DB_LOCK: 
        # Fetch all reservation IDs for this room.
        room_res_ids = RESERVATION_IDS_BY_ROOM[req.room_id] 

        # Check against existing reservations for overlap.
        for existing_id in room_res_ids:  
            existing = RESERVATIONS_BY_ID[existing_id]  
            ex_start = existing["start_time"] 
            ex_end = existing["end_time"]  
            if overlaps(start_utc, end_utc, ex_start, ex_end):  
                raise HTTPException( 
                    status_code=409,  
                    detail="Reservation overlaps with an existing reservation for this room.",
                )  

        # Generate a new random reservation ID.
        reservation_id = str(uuid4())

        # Store the reservation record (in UTC for stable comparisons).
        record = {  
            "reservation_id": reservation_id, 
            "user_id": req.user_id,  
            "room_id": req.room_id, 
            "start_time": start_utc,  
            "end_time": end_utc,  
        }  

        RESERVATIONS_BY_ID[reservation_id] = record  
        RESERVATION_IDS_BY_ROOM[req.room_id].append(reservation_id)  

    # Return response (times are UTC datetimes).
    return ReservationResponse(**record) 


@app.delete("/reservations/{reservation_id}", response_model=CancelResponse)  # Define endpoint to cancel a reservation.
def cancel_reservation(reservation_id: str = Path(..., min_length=1, max_length=64)) -> CancelResponse:
    """
    Cancel an existing room reservation.

    This endpoint removes the reservation from the system and frees
    the associated time slot for future bookings.

    Attempting to cancel a non-existent
    reservation will result in an error.

    Raises:
        HTTPException(404): If the reservation does not exist
    """ 
    with DB_LOCK:  
        if reservation_id not in RESERVATIONS_BY_ID:  
            raise HTTPException(status_code=404, detail="Reservation not found.")  

        record = RESERVATIONS_BY_ID.pop(reservation_id)  
        room_id = record["room_id"]  

        
        room_list = RESERVATION_IDS_BY_ROOM.get(room_id, [])  
        if reservation_id in room_list:  
            room_list.remove(reservation_id)  

    return CancelResponse(cancelled=True, reservation_id=reservation_id)  


@app.get("/rooms/{room_id}/reservations", response_model=List[ReservationResponse])  
def list_reservations_for_room(
    room_id: str = Path(..., min_length=1, max_length=32),  
    user_id: Optional[str] = None,  
) -> List[ReservationResponse]:
    require_room_exists(room_id)  

    """
    List reservations for a specific room.

    Reservations are returned in ascending order by start time.
    Results can optionally be filtered by user ID.

    Raises:
        HTTPException(404): If the specified room does not exist
    """

    with DB_LOCK:  
        res_ids = list(RESERVATION_IDS_BY_ROOM[room_id])  
        records = [RESERVATIONS_BY_ID[rid] for rid in res_ids]  

    
    if user_id is not None:  
        records = [r for r in records if r["user_id"] == user_id]  

    
    records.sort(key=lambda r: r["start_time"])  

    return [ReservationResponse(**r) for r in records]  
