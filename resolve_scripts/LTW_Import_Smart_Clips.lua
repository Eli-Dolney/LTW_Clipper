-- LTW Import Smart Clips
-- Imports clips selected by transcript analysis (Opus Clip-style)
-- Author: LTW Video Editor Pro

local function get_smart_clips_file()
    local ui = fu.UIManager
    local disp = bmd.UIDispatcher(ui)
    
    local win = disp:AddWindow({
        ID = 'SmartWin',
        WindowTitle = 'LTW Import Smart Clips',
        Geometry = {100, 100, 450, 150},
        Spacing = 10,
        
        ui:VGroup{
            ui:Label{ID = 'Label', Text = 'Smart Clips JSON:', Weight = 0},
            ui:LineEdit{ID = 'PathInput', PlaceholderText = '/path/to/smart_clips.json'},
            ui:Label{ID = 'Label2', Text = 'Source Video:', Weight = 0},
            ui:LineEdit{ID = 'VideoInput', PlaceholderText = '/path/to/source_video.mp4'},
            ui:VGap(10),
            ui:HGroup{
                Weight = 0,
                ui:Button{ID = 'ImportBtn', Text = 'Create Timeline'},
                ui:Button{ID = 'CancelBtn', Text = 'Cancel'}
            }
        }
    })
    
    local itm = win:GetItems()
    local result = nil
    
    function win.On.ImportBtn.Clicked(ev)
        result = {
            json_path = itm.PathInput.Text,
            video_path = itm.VideoInput.Text
        }
        disp:ExitLoop()
    end
    
    function win.On.CancelBtn.Clicked(ev)
        disp:ExitLoop()
    end
    
    function win.On.SmartWin.Close(ev)
        disp:ExitLoop()
    end
    
    win:Show()
    disp:RunLoop()
    win:Hide()
    
    return result
end

local function import_smart_clips(settings)
    if not settings or settings.json_path == "" then return end
    
    local file = io.open(settings.json_path, "r")
    if not file then
        print("Could not open: " .. settings.json_path)
        return
    end
    
    local content = file:read("*a")
    file:close()
    
    -- Parse JSON (simplified)
    local clips = {}
    for start, end_time, text in string.gmatch(content, '"start":%s*([%d%.]+).-"end":%s*([%d%.]+).-"text":%s*"([^"]+)"') do
        table.insert(clips, {
            start = tonumber(start),
            end_time = tonumber(end_time),
            text = text
        })
    end
    
    if #clips == 0 then
        print("No clips found in JSON.")
        return
    end
    
    print("Found " .. #clips .. " smart clips.")
    
    local projectManager = resolve:GetProjectManager()
    local project = projectManager:GetCurrentProject()
    local mediaPool = project:GetMediaPool()
    
    -- Import source video
    local video_items = mediaPool:ImportMedia(settings.video_path)
    if not video_items or #video_items == 0 then
        print("Could not import video: " .. settings.video_path)
        return
    end
    
    local source_clip = video_items[1]
    
    -- Create timeline
    local timeline = mediaPool:CreateEmptyTimeline("Smart_Clips_Timeline")
    
    -- Create subclips for each smart clip
    for i, clip_info in ipairs(clips) do
        print(string.format("Creating clip %d/%d: %.1fs - %.1fs", i, #clips, clip_info.start, clip_info.end_time))
        
        -- Create subclip in media pool
        local fps = project:GetSetting("timelineFrameRate")
        local start_frame = math.floor(clip_info.start * fps)
        local end_frame = math.floor(clip_info.end_time * fps)
        
        local subclip = {
            ["mediaPoolItem"] = source_clip,
            ["startFrame"] = start_frame,
            ["endFrame"] = end_frame
        }
        
        mediaPool:AppendToTimeline({subclip})
    end
    
    print("✅ Timeline created with " .. #clips .. " smart clips!")
end

local settings = get_smart_clips_file()
import_smart_clips(settings)

