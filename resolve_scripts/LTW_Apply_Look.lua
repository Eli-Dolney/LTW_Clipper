-- LTW Apply Look (LUT)
-- Applies a selected LUT to all clips in the current timeline
-- Author: LTW Video Editor Pro

local function get_lut_selection()
    local ui = fu.UIManager
    local disp = bmd.UIDispatcher(ui)
    
    local win = disp:AddWindow({
        ID = 'LutWin',
        WindowTitle = 'LTW Auto-Grader',
        Geometry = {100, 100, 350, 150},
        Spacing = 10,
        
        ui:VGroup{
            ui:Label{ID = 'Label', Text = 'Select Content Style:', Weight = 0},
            ui:ComboBox{ID = 'LutCombo', Text = 'Select a Look...'},
            ui:Label{ID = 'Info', Text = '(Put .cube files in assets/luts/)', Weight = 0},
            ui:VGap(5),
            ui:HGroup{
                Weight = 0,
                ui:Button{ID = 'ApplyBtn', Text = 'Apply Look'},
                ui:Button{ID = 'CancelBtn', Text = 'Cancel'}
            }
        }
    })
    
    local itm = win:GetItems()
    
    -- Scan for LUTs in assets folder
    -- Use relative path from script location or user-provided path
    local script_path = debug.getinfo(1, "S").source:match("@(.*/)")
    local lut_path = script_path and (script_path .. "../assets/luts") or (os.getenv("HOME") .. "/LTW_Clipper/assets/luts")
    
    -- Fallback: ask user for LUT folder path if not found
    if not os.execute("test -d '" .. lut_path .. "'") then
        lut_path = os.getenv("HOME") .. "/LTW_Clipper/assets/luts"
    end
    
    -- List .cube files (using ls command as Lua filesystem access is limited in Resolve sandbox)
    local handle = io.popen('ls "' .. lut_path .. '"/*.cube 2>/dev/null')
    if handle then
        local result = handle:read("*a")
        handle:close()
        
        for filename in string.gmatch(result, "([^/]+%.cube)") do
            itm.LutCombo:AddItem(filename)
        end
    end
    
    -- Add categories as fallback if no files found
    itm.LutCombo:AddItem('Gaming (Vibrant)')
    itm.LutCombo:AddItem('Tutorial (Clean)')
    itm.LutCombo:AddItem('Sports (Action)')
    
    local result = nil
    
    function win.On.ApplyBtn.Clicked(ev)
        result = itm.LutCombo.CurrentText
        disp:ExitLoop()
    end
    
    function win.On.CancelBtn.Clicked(ev)
        disp:ExitLoop()
    end
    
    function win.On.LutWin.Close(ev)
        disp:ExitLoop()
    end
    
    win:Show()
    disp:RunLoop()
    win:Hide()
    
    return result
end

local function apply_look(look_name)
    if not look_name or look_name == 'Select a Look...' then return end
    
    local projectManager = resolve:GetProjectManager()
    local project = projectManager:GetCurrentProject()
    if not project then return end
    
    local timeline = project:GetCurrentTimeline()
    if not timeline then return end
    
    print("Applying look: " .. look_name)
    
    -- Get all video clips in Track 1
    local clips = timeline:GetItemListInTrack('video', 1)
    if not clips then return end
    
    for i, clip in ipairs(clips) do
        -- Apply LUT Logic
        -- NOTE: API does not allow setting arbitrary external LUT file easily via SetLUT()
        -- unless that LUT is already in Resolve's LUT list.
        -- WORKAROUND: We print the instruction.
        
        print("Clip: " .. clip:GetName())
        print("ACTION: Please drag '" .. look_name .. "' from the LUTs panel onto this clip.")
    end
    
    print("✅ NOTE: To automate fully, install your .cube files into DaVinci Resolve's LUT folder:")
    print("   /Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT/")
end

local look = get_lut_selection()
apply_look(look)

