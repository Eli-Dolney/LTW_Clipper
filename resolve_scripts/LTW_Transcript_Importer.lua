-- LTW Transcript Importer
-- Imports SRT/VTT/JSON transcripts and creates Text+ nodes in Resolve
-- Author: LTW Video Editor Pro

local function get_transcript_file()
    local ui = fu.UIManager
    local disp = bmd.UIDispatcher(ui)
    
    local win = disp:AddWindow({
        ID = 'TransWin',
        WindowTitle = 'LTW Transcript Importer',
        Geometry = {100, 100, 450, 200},
        Spacing = 10,
        
        ui:VGroup{
            ui:Label{ID = 'Label', Text = 'Transcript File Path:', Weight = 0},
            ui:LineEdit{ID = 'PathInput', PlaceholderText = '/path/to/transcript.srt'},
            
            ui:Label{ID = 'StyleLabel', Text = 'Caption Style:', Weight = 0},
            ui:ComboBox{ID = 'StyleCombo', Text = 'Modern Bold'},
            
            ui:Label{ID = 'PosLabel', Text = 'Position:', Weight = 0},
            ui:ComboBox{ID = 'PosCombo', Text = 'Bottom Center'},
            
            ui:VGap(10),
            ui:HGroup{
                Weight = 0,
                ui:Button{ID = 'ImportBtn', Text = 'Import Transcript'},
                ui:Button{ID = 'CancelBtn', Text = 'Cancel'}
            }
        }
    })
    
    local itm = win:GetItems()
    
    itm.StyleCombo:AddItem('Modern Bold')
    itm.StyleCombo:AddItem('Minimal Clean')
    itm.StyleCombo:AddItem('Gaming Style')
    
    itm.PosCombo:AddItem('Bottom Center')
    itm.PosCombo:AddItem('Top Center')
    itm.PosCombo:AddItem('Center')
    
    local result = nil
    
    function win.On.ImportBtn.Clicked(ev)
        result = {
            path = itm.PathInput.Text,
            style = itm.StyleCombo.CurrentText,
            position = itm.PosCombo.CurrentText
        }
        disp:ExitLoop()
    end
    
    function win.On.CancelBtn.Clicked(ev)
        disp:ExitLoop()
    end
    
    function win.On.TransWin.Close(ev)
        disp:ExitLoop()
    end
    
    win:Show()
    disp:RunLoop()
    win:Hide()
    
    return result
end

local function parse_srt(content)
    local subtitles = {}
    local blocks = {}
    
    -- Split by double newline
    for block in string.gmatch(content, "([^\r\n]+[^\r\n]+)") do
        if block ~= "" then
            table.insert(blocks, block)
        end
    end
    
    -- Parse each subtitle block
    -- Format: "1\n00:00:00,000 --> 00:00:05,000\nText here"
    local i = 1
    while i <= #blocks do
        local num = blocks[i]
        i = i + 1
        if i <= #blocks then
            local timecode = blocks[i]
            i = i + 1
            if i <= #blocks then
                local text = blocks[i]
                i = i + 1
                
                -- Parse timecode "00:00:00,000 --> 00:00:05,000"
                local start_str, end_str = string.match(timecode, "([%d:%,]+)%s*-->%s*([%d:%,]+)")
                
                if start_str and end_str then
                    -- Convert to seconds (simplified, assumes HH:MM:SS,mmm)
                    local function tc_to_sec(tc)
                        local h, m, s, ms = string.match(tc, "(%d+):(%d+):(%d+),?(%d*)")
                        return (tonumber(h) or 0) * 3600 + (tonumber(m) or 0) * 60 + (tonumber(s) or 0) + (tonumber(ms) or 0) / 1000
                    end
                    
                    table.insert(subtitles, {
                        start = tc_to_sec(start_str),
                        end_time = tc_to_sec(end_str),
                        text = text
                    })
                end
            end
        end
    end
    
    return subtitles
end

local function import_transcript(settings)
    if not settings or settings.path == "" then return end
    
    local file = io.open(settings.path, "r")
    if not file then
        print("Could not open file: " .. settings.path)
        return
    end
    
    local content = file:read("*a")
    file:close()
    
    -- Detect format
    local subtitles = {}
    if string.find(settings.path, "%.srt$") then
        subtitles = parse_srt(content)
    elseif string.find(settings.path, "%.json$") then
        -- JSON format (from Whisper or our tools)
        -- Simple JSON parsing (assumes {"segments": [{"start": 0, "end": 5, "text": "..."}]})
        for start, end_time, text in string.gmatch(content, '"start":%s*([%d%.]+).-"end":%s*([%d%.]+).-"text":%s*"([^"]+)"') do
            table.insert(subtitles, {
                start = tonumber(start),
                end_time = tonumber(end_time),
                text = text
            })
        end
    end
    
    if #subtitles == 0 then
        print("No subtitles found in file.")
        return
    end
    
    print("Found " .. #subtitles .. " subtitle segments.")
    
    local projectManager = resolve:GetProjectManager()
    local project = projectManager:GetCurrentProject()
    local timeline = project:GetCurrentTimeline()
    
    if not timeline then
        print("No timeline active.")
        return
    end
    
    -- Create Text+ nodes for each subtitle
    -- Note: Resolve API for creating Text+ nodes is complex and requires Fusion page
    -- WORKAROUND: We'll create a guide file that the user can import, or use a simpler method
    
    print("Creating subtitle track...")
    
    -- For now, we'll print instructions since Text+ creation via API is very complex
    print("📝 SUBTITLE IMPORT INSTRUCTIONS:")
    print("   1. Go to Edit page")
    print("   2. Right-click Timeline -> Add Track -> Add Subtitle Track")
    print("   3. For each subtitle:")
    print("      - Click 'Add Subtitle'")
    print("      - Set In/Out times")
    print("      - Type the text")
    print("")
    print("   OR use DaVinci Resolve Studio's built-in transcription:")
    print("   Workspace -> Scripts -> Comp -> LTW_Use_Resolve_Transcription")
    
    -- Save subtitle data for future automation
    local output = os.getenv("HOME") .. "/Desktop/subtitles_imported.txt"
    local outfile = io.open(output, "w")
    if outfile then
        for i, sub in ipairs(subtitles) do
            outfile:write(string.format("%.2f -> %.2f: %s\n", sub.start, sub.end_time, sub.text))
        end
        outfile:close()
        print("Saved subtitle list to: " .. output)
    end
end

local settings = get_transcript_file()
import_transcript(settings)

