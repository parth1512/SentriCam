# Telegram Notification Conditions and Situations

This document explains all conditions and situations where Telegram notifications will be sent to users based on the current code configuration.

## 📋 Prerequisites for ALL Notifications

For **ANY** notification to be sent, the following conditions MUST be met:

1. **Vehicle Registration**: The vehicle plate number must be registered in the database (`vehicles` table)
2. **Telegram Chat ID**: The vehicle must have a `telegram_chat_id` linked (user must register via Telegram bot using `/start`)
3. **Telegram Bot Enabled**: `TELEGRAM_BOT_TOKEN` must be set and `TELEGRAM_ENABLED=true`
4. **Bot Initialized**: Telegram bot must be successfully initialized and running
5. **Valid Location Data**: For location-based notifications, camera must have valid `lat` and `lng` coordinates

---

## 🔔 Notification Types and When They're Sent

### 1. **ENTRY Notification** (`event_type='entry'`)

#### When Sent:
- **First Detection on Camera1**: When a vehicle is detected for the FIRST TIME on `camera1`
- **Trigger**: Immediate (sent as soon as detection is confirmed)

#### Message Content:
- Vehicle entry alert message
- Timestamp in IST (Indian Standard Time)
- **NO location/map included** (cleaner first notification)
- Message: "Location details will be shared once the vehicle moves to a different area."

#### Conditions:
- ✅ Vehicle detected on `camera1`
- ✅ Vehicle not in `vehicle_first_seen` dictionary (first detection ever)
- ✅ Vehicle not in `vehicle_exits` dictionary (not marked as exited)
- ✅ Vehicle passes all prerequisites above

#### Code Location:
```python
# app.py, line 547-560
if is_first_detection and camera_id == 'camera1':
    send_telegram_notification(text, camera_id, location_data, 
                              event_type='entry', include_location=False)
```

---

### 2. **EXIT Notification** (`event_type='exit'`)

#### When Sent:
- **Second Detection on Camera1**: When a vehicle is detected on `camera1` for the SECOND time
- **Trigger**: Immediate (sent as soon as second detection is confirmed)

#### Message Content:
- Vehicle exit alert message
- Exit location (camera1 name)
- Timestamp in IST
- **NO location/map included** (as per requirement)

#### Conditions:
- ✅ Vehicle detected on `camera1`
- ✅ `camera1_detection_count[plate] == 2` (second detection)
- ✅ Vehicle passes all prerequisites above
- ✅ Any active timer is cancelled before sending notification

#### Code Location:
```python
# app.py, line 417-440
if camera_id == 'camera1':
    camera1_count = camera1_detection_count[text]
    if camera1_count == 2:
        send_telegram_notification(text, camera_id, location_data, 
                                  event_type='exit', include_location=False)
```

#### Important Notes:
- Timer is cancelled immediately when exit is detected
- Vehicle is marked as `vehicle_exits[text] = True`
- Tracking data is cleaned up (vehicle can be tracked again if it re-enters)
- Only applies to `camera1` - other cameras don't trigger exit

---

### 3. **LAST SEEN Notification** (`event_type='last_seen'`)

#### When Sent:
- **Timer Expiry**: When a 30-second timer expires without new detections
- **Trigger**: 30 seconds after last detection at a camera location

#### Message Content:
- Last seen location update
- Location name (camera name)
- Estimated range (50 meters)
- Timestamp in IST
- **Google Maps link** with coordinates (clickable location)
- **Location pin** sent to Telegram (if coordinates are valid)

#### Conditions:
- ✅ 30-second timer expires without new detections
- ✅ Valid location data with `lat` and `lng` coordinates
- ✅ Vehicle not in `vehicle_exits` dictionary
- ✅ Vehicle passes all prerequisites above

#### Code Location:
```python
# app.py, line 204-287 (on_timer_expire function)
# Timer expires after 30 seconds
send_telegram_notification(plate_number, last_camera, last_location, 
                          event_type='last_seen', include_location=True)
```

#### When Timer Starts:
1. **After First Detection on Camera1**: Timer starts immediately after first detection on camera1 (30s timer)
2. **After Movement to Different Camera**: Timer starts when vehicle moves from camera1 to a different camera (30s timer)
3. **Timer Restarts**: Timer restarts (cancels old, starts new) when:
   - Vehicle moves to different camera (timer restarts silently - no notification)
   - Vehicle detected again at same camera (timer restarts silently - no notification)

#### Timer Behavior:
- **Movement to Different Camera**: Timer is cancelled and restarted (no notification sent)
- **Same Camera Re-detection**: Timer is cancelled and restarted (no notification sent)
- **No New Detection for 30s**: Timer expires → **LAST SEEN notification sent**

---

## ❌ Situations Where NO Notification is Sent

### 1. **Movement Between Cameras**
- When vehicle moves from one camera to another
- Timer is restarted silently (30s reset)
- **NO notification sent** - user gets 30 more seconds
- Notification only sent when timer expires (last_seen)

### 2. **Re-detection at Same Camera**
- When vehicle is detected again at the same camera
- Timer is restarted silently
- **NO notification sent** - user gets 30 more seconds
- Notification only sent when timer expires (last_seen)

### 3. **Vehicle Already Exited**
- When vehicle is marked as exited (`vehicle_exits[text] = True`)
- All detections are skipped
- **NO notifications sent** for exited vehicles

### 4. **Missing Prerequisites**
- Vehicle not registered in database → **NO notification**
- No Telegram chat ID linked → **NO notification**
- Telegram bot not initialized → **NO notification**
- Missing location coordinates → **NO notification** (for last_seen)

### 5. **First Detection on Other Cameras (Not Camera1)**
- First detection on cameras other than camera1 does **NOT** send ENTRY notification
- Only first detection on `camera1` triggers ENTRY notification
- Exit only triggered on **SECOND detection** on camera1

---

## 🔄 Notification Flow Diagram

```
Vehicle Detected
    │
    ├─ On camera1?
    │   ├─ First Detection? → Send ENTRY notification (no location)
    │   │                     Start 30s timer
    │   │                     └─ Timer expires? → Send LAST SEEN notification (with location)
    │   │
    │   └─ Second Detection? → Send EXIT notification (no location)
    │                          Cancel timer
    │                          Mark as exited
    │
    ├─ On Other Camera?
    │   ├─ First Detection? → Start 30s timer (no ENTRY notification)
    │   │                     └─ Timer expires? → Send LAST SEEN notification (with location)
    │   │
    │   ├─ Different camera? → Restart timer (no notification)
    │   ├─ Same camera? → Restart timer (no notification)
    │   └─ Timer expires? → Send LAST SEEN notification (with location)
    │
    └─ Vehicle Exited?
        └─ YES → Skip all detections (no notifications)
```

---

## 📊 Notification Summary Table

| Event Type | When Sent | Location Included | Map Link | Timing |
|------------|-----------|-------------------|----------|--------|
| **ENTRY** | First detection on camera1 | ❌ No | ❌ No | Immediate |
| **EXIT** | Second detection on camera1 | ❌ No | ❌ No | Immediate |
| **LAST SEEN** | 30s timer expires | ✅ Yes | ✅ Yes | After 30s |

---

## 🔍 Detailed Scenarios

### Scenario 1: Vehicle Enters via Camera1 and Stays
1. Vehicle detected at `camera1` (first time)
   - ✅ **ENTRY notification sent** (no location)
   - ⏱️ 30s timer starts
2. Vehicle detected again at `camera1` (within 30s, but not second time yet)
   - ⏱️ Timer restarts (no notification)
3. No more detections for 30s
   - ✅ **LAST SEEN notification sent** (with location and map)

### Scenario 2: Vehicle Enters via Camera1 and Moves to Other Cameras
1. Vehicle detected at `camera1` (first time)
   - ✅ **ENTRY notification sent** (no location)
   - ⏱️ 30s timer starts
2. Vehicle detected at `camera2` (within 30s)
   - ⏱️ Timer restarts at camera2 (no notification)
3. Vehicle detected at `camera3` (within 30s)
   - ⏱️ Timer restarts at camera3 (no notification)
4. No more detections for 30s
   - ✅ **LAST SEEN notification sent** (camera3 location with map)

### Scenario 3: Vehicle Enters via Camera1, Moves, Then Exits via Camera1
1. Vehicle detected at `camera1` (first time)
   - ✅ **ENTRY notification sent** (no location)
   - ⏱️ 30s timer starts
2. Vehicle detected at `camera2` (within 30s)
   - ⏱️ Timer restarts at camera2 (no notification)
3. Vehicle detected at `camera1` again (second time)
   - ✅ **EXIT notification sent** (no location)
   - ⏱️ Timer cancelled
   - 🚫 Vehicle marked as exited (no more notifications)

### Scenario 4: Vehicle Enters via Camera1, Moves Between Cameras, Then Exits
1. Vehicle detected at `camera1` (first time)
   - ✅ **ENTRY notification sent** (no location)
   - ⏱️ 30s timer starts
2. Vehicle detected at `camera2` (within 30s)
   - ⏱️ Timer restarts at camera2 (no notification)
3. Vehicle detected at `camera3` (within 30s)
   - ⏱️ Timer restarts at camera3 (no notification)
4. Vehicle detected at `camera1` (second time on camera1)
   - ✅ **EXIT notification sent** (no location)
   - ⏱️ Timer cancelled

### Scenario 5: Vehicle Enters via Other Camera (Not Camera1)
1. Vehicle detected at `camera2` (first time, but not camera1)
   - ❌ **NO ENTRY notification sent**
   - ⏱️ 30s timer starts (if movement tracking enabled)
2. Vehicle detected again at `camera2` (within 30s)
   - ⏱️ Timer restarts (no notification)
3. No more detections for 30s
   - ✅ **LAST SEEN notification sent** (with location and map)

---

## ⚙️ Configuration Requirements

### Environment Variables:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ENABLED=true
```

### Database Requirements:
- `vehicles` table must exist
- Vehicle must have `vehicle_number` (normalized: uppercase, stripped)
- Vehicle must have `telegram_chat_id` (set via Telegram bot registration)
- Vehicle may have `name` (user name - optional)

### Camera Configuration:
- Each camera must have location data with `lat` and `lng`
- Camera location must have `name` (for display in notifications)
- Camera ID `camera1` is special (triggers exit on second detection)

---

## 🐛 Troubleshooting

### Notification Not Sent? Check:

1. **Vehicle Registration**
   - Is vehicle registered in database?
   - Check: `Vehicle.query.filter_by(vehicle_number=plate).first()`

2. **Telegram Chat ID**
   - Does vehicle have `telegram_chat_id`?
   - User must register via Telegram bot (`/start` command)

3. **Telegram Bot Status**
   - Is bot initialized?
   - Is `TELEGRAM_BOT_TOKEN` set?
   - Check server logs for bot initialization errors

4. **Location Data**
   - Does camera have valid `lat` and `lng`?
   - Check camera configuration in `cameras` dictionary

5. **Timer Status**
   - Is timer running? (Check `vehicle_timers` dictionary)
   - Did timer expire? (Check server logs for "TIMER EXPIRED")
   - Was timer cancelled? (Check for "Cancelled previous timer" logs)

6. **Exit Status**
   - Is vehicle marked as exited? (Check `vehicle_exits` dictionary)
   - Exited vehicles don't receive notifications

---

## 📝 Notes

- **Timer Duration**: Fixed at 30 seconds (not configurable)
- **Location Precision**: 50 meters estimated range for last_seen notifications
- **Time Format**: All timestamps converted to IST (UTC+5:30)
- **Plate Normalization**: All plate numbers normalized to uppercase and stripped
- **Camera1 Special Logic**: Only `camera1` triggers exit on second detection
- **No Movement Notifications**: Movement between cameras doesn't send notifications (only timer expiry sends last_seen)
- **Timer Restarts**: Timer restarts silently on new detections (no notification until expiry)

---

## 🔗 Related Files

- `app.py`: Main detection and notification logic
- `services/telegram_bot.py`: Telegram bot and notification sending
- `models.py`: Database models (Vehicle table)
- `on_timer_expire()`: Timer expiry handler
- `send_telegram_notification()`: Notification wrapper function
- `send_vehicle_event()`: Telegram notification sender

---

## 📅 Last Updated

Document created based on code analysis of current implementation.
Review code in `app.py` and `services/telegram_bot.py` for latest changes.

