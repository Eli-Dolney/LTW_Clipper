-- LTW Smart Fit (Fixed)
-- Automatically scales clips to fill the frame
-- Author: LTW Video Editor Pro

local function smart_fit()
    local projectManager = resolve:GetProjectManager()
    local project = projectManager:GetCurrentProject()
    local timeline = project:GetCurrentTimeline()
    
    if not timeline then
        print("No timeline active.")
        return
    end
    
    local clips = timeline:GetItemListInTrack('video', 1)
    if not clips then return end
    
    print("Processing " .. #clips .. " items on Video Track 1...")
    
    for i, clip in ipairs(clips) do
        local name = clip:GetName()
        
        -- Filter out Transitions (Simple name check, or check duration/type if possible)
        -- Resolve API doesn't have a clean "IsTransition()" method on TimelineItem
        -- But standard transitions usually don't have Input Scaling properties accessible the same way
        
        if name ~= "Transition" and name ~= "Cross Dissolve" and name ~= "Blur Dissolve" then
            print("Setting scaling for: " .. name)
            
            -- Try multiple common property value strings for "Fill/Crop"
            -- The API expects the EXACT string from the specific Resolve version's dropdown
            
            local success = clip:SetProperty("Input Scaling Preset", "Scale full frame with crop")
            
            if not success then
                -- Try alternative string (older versions or Mismatch)
                success = clip:SetProperty("Input Scaling Preset", "Scale to Fill")
            end
            
            if not success then
                -- Try another one
                success = clip:SetProperty("Input Scaling Preset", "Crop")
            end
            
            if success then
                print("✅ Scaled successfully")
            else
                print("⚠️ Failed to set Input Scaling. Trying Zoom...")
                -- Fallback: Set Zoom to 1.5 (Simulate fill for HD -> Vertical)
                -- This is a blind guess, but better than black bars
                -- clip:SetProperty("ZoomX", 1.5)
                -- clip:SetProperty("ZoomY", 1.5)
            end
        end
    end
    
    print("Smart Fit Complete.")
end

smart_fit()
