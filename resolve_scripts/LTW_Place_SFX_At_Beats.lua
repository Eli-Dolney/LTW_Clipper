-- LTW SFX + Transition Placer
-- Reads a Beat Map JSON (from beat_detector.py) and, on the current timeline:
--   1) Imports an SFX pack folder into a "LTW SFX" bin
--   2) Drops an SFX hit at every beat on a dedicated audio track (cycling the pack)
--   3) Adds a colored marker at every beat noting which transition to apply
--
-- Why markers for transitions? The DaVinci Resolve scripting API cannot add
-- video transitions directly, so we place the SFX automatically and mark every
-- cut so you can select-all + Cmd+T (or drag your .drfx transition) in one pass.
-- Author: LTW Video Editor Pro

local function read_file(path)
    local f = io.open(path, "r")
    if not f then return nil end
    local content = f:read("*a")
    f:close()
    return content
end

local function parse_beats(content)
    -- Pull numbers out of the "beats": [ ... ] array of our JSON format.
    local beats = {}
    local in_beats = false
    for line in string.gmatch(content, "[^\r\n]+") do
        if string.find(line, '"beats"') then in_beats = true end
        if in_beats then
            for num in string.gmatch(line, "([%d]+%.?[%d]*)") do
                local v = tonumber(num)
                if v ~= nil then table.insert(beats, v) end
            end
        end
        if in_beats and string.find(line, "%]") then break end
    end
    -- First match may be the count from elsewhere; rely on monotonic increase.
    table.sort(beats)
    return beats
end

local function get_settings()
    local ui = fu.UIManager
    local disp = bmd.UIDispatcher(ui)

    local win = disp:AddWindow({
        ID = 'SfxWin',
        WindowTitle = 'LTW SFX + Transition Placer',
        Geometry = {100, 100, 480, 230},
        Spacing = 10,
        ui:VGroup{
            ui:Label{ID = 'L1', Text = 'Beat Map JSON (from beat_detector.py):', Weight = 0},
            ui:LineEdit{ID = 'BeatPath', PlaceholderText = '/path/to/song.json'},
            ui:Label{ID = 'L2', Text = 'SFX Pack Folder (whooshes, impacts, risers):', Weight = 0},
            ui:LineEdit{ID = 'SfxPath', PlaceholderText = '/path/to/transition_sfx_folder'},
            ui:Label{ID = 'L3', Text = 'Transition name (for marker notes):', Weight = 0},
            ui:LineEdit{ID = 'TransName', Text = 'Cross Dissolve'},
            ui:VGap(6),
            ui:HGroup{
                Weight = 0,
                ui:Button{ID = 'GoBtn', Text = 'Place SFX + Mark Cuts'},
                ui:Button{ID = 'CancelBtn', Text = 'Cancel'}
            }
        }
    })
    local itm = win:GetItems()
    local result = nil

    function win.On.GoBtn.Clicked(ev)
        result = {
            beat_path = itm.BeatPath.Text,
            sfx_path = itm.SfxPath.Text,
            transition = itm.TransName.Text,
        }
        disp:ExitLoop()
    end
    function win.On.CancelBtn.Clicked(ev) disp:ExitLoop() end
    function win.On.SfxWin.Close(ev) disp:ExitLoop() end

    win:Show()
    disp:RunLoop()
    win:Hide()
    return result
end

local function place(settings)
    if not settings or settings.beat_path == "" then
        print("No beat map provided.")
        return
    end

    local content = read_file(settings.beat_path)
    if not content then
        print("Could not read beat map: " .. settings.beat_path)
        return
    end
    local beats = parse_beats(content)
    if #beats == 0 then
        print("No beats found in JSON.")
        return
    end
    print("Loaded " .. #beats .. " beats.")

    local resolve = Resolve()
    local pm = resolve:GetProjectManager()
    local project = pm:GetCurrentProject()
    local mediaPool = project:GetMediaPool()
    local timeline = project:GetCurrentTimeline()
    if not timeline then
        print("Open a timeline first.")
        return
    end

    local fps = tonumber(project:GetSetting("timelineFrameRate")) or 30.0

    -- 1) Import SFX pack into a dedicated bin (if a folder was provided).
    local sfx_clips = {}
    if settings.sfx_path and settings.sfx_path ~= "" then
        local root = mediaPool:GetRootFolder()
        local bin = mediaPool:AddSubFolder(root, "LTW SFX")
        mediaPool:SetCurrentFolder(bin or root)
        local imported = mediaPool:ImportMedia({settings.sfx_path})
        if imported then
            for _, c in ipairs(imported) do table.insert(sfx_clips, c) end
        end
        print("Imported " .. #sfx_clips .. " SFX files.")
    end

    -- 2) Place an SFX hit at each beat (cycling through the pack) using recordFrame.
    if #sfx_clips > 0 then
        local idx = 1
        local placed = 0
        for _, t in ipairs(beats) do
            local rec = math.floor(t * fps)
            local clip = sfx_clips[idx]
            local entry = {
                ["mediaPoolItem"] = clip,
                ["startFrame"] = 0,
                ["endFrame"] = math.floor(0.6 * fps),
                ["recordFrame"] = rec,
                ["trackIndex"] = 2,
                ["mediaType"] = 2, -- audio only
            }
            if mediaPool:AppendToTimeline({entry}) then placed = placed + 1 end
            idx = idx + 1
            if idx > #sfx_clips then idx = 1 end
        end
        print("Placed " .. placed .. " SFX hits on audio track 2.")
    else
        print("No SFX folder given - skipping SFX placement, adding markers only.")
    end

    -- 3) Add a marker at every beat with the transition note.
    local note = "Apply: " .. (settings.transition or "transition") .. " (Cmd+T or drag .drfx)"
    local marked = 0
    for _, t in ipairs(beats) do
        local frame = math.floor(t * fps)
        if timeline:AddMarker(frame, "Cyan", "LTW Cut", note, 1) then
            marked = marked + 1
        end
    end
    print("Added " .. marked .. " transition markers.")
    print("Done. Select all clips and press Cmd+T to apply your transition at every marked cut.")
end

local settings = get_settings()
place(settings)
