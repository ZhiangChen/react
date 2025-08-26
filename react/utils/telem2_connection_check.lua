-- telem2_connection_lost_alert.lua
local PARAM_NAME = "SCR_USER1"   -- Python updates this via MAVLink PARAM_SET
local LOST_MSG_PERIOD = 5000    -- ms, time between "connection lost" messages
local TIMEOUT_MS = 3000          -- ms, time before considering the link dead

local last_seen = 0
local last_lost_msg = 0
local last_val = nil
local sysid = (param:get("SYSID_THISMAV") or 1)
local connection_lost_notified = false
local initialized = false

local function update()
  local now = millis()
  
  -- Safety check for millis() function
  if not now then
    gcs:send_text(6, "Lua error: millis() returned nil")
    return update, 1000
  end
  
  -- Initialize last_seen on first run
  if not initialized then
    last_seen = now
    last_lost_msg = now
    initialized = true
  end
  
  local v = param:get(PARAM_NAME)
  
  -- Check for parameter updates (connection alive)
  if v ~= nil then
    if last_val == nil or v ~= last_val then
      last_val = v
      last_seen = now
      -- Reset the lost notification flag when connection is restored
      if connection_lost_notified then
        connection_lost_notified = false
        gcs:send_text(0, "telem2 connection restored")
      end
    end
  end

  -- Check if connection is lost and send periodic alerts
  local time_since_last_seen = now - last_seen
  local time_since_last_msg = now - last_lost_msg
  local connection_lost = time_since_last_seen >= TIMEOUT_MS
  
  if connection_lost and time_since_last_msg >= LOST_MSG_PERIOD then
    last_lost_msg = now
    connection_lost_notified = true
    local seconds_lost = time_since_last_seen / 1000
    seconds_lost = seconds_lost - (seconds_lost % 1)  -- Simple integer conversion
    gcs:send_text(0, "telem2 connection LOST (" .. tostring(seconds_lost) .. "s ago)")
  end

  return update, 100
end

return update()
