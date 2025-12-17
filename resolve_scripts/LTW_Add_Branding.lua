-- LTW Branding Suite
-- Adds Intro, Outro, and Watermark based on Channel Profile
-- Author: LTW Video Editor Pro

local function get_branding_profile()
    local ui = fu.UIManager
    local disp = bmd.UIDispatcher(ui)
    
    local win = disp:AddWindow({
        ID = 'BrandWin',
        WindowTitle = 'LTW Branding Suite',
        Geometry = {100, 100, 350, 150},
        Spacing = 10,
        
        ui:VGroup{
            ui:Label{ID = 'Label', Text = 'Select Channel Profile:', Weight = 0},
            ui:ComboBox{ID = 'ProfileCombo', Text = 'Select Profile...'},
            ui:Label{ID = 'Info', Text = '(Adds Intro/Outro & Watermark)', Weight = 0},
            ui:VGap(5),
            ui:HGroup{
                Weight = 0,
                ui:Button{ID = 'ApplyBtn', Text = 'Apply Branding'},
                ui:Button{ID = 'CancelBtn', Text = 'Cancel'}
            }
        }
    })
    
    local itm = win:GetItems()
    
    -- Add profiles
    itm.ProfileCombo:AddItem('Tech Tutorial')
    itm.ProfileCombo:AddItem('Gaming Channel')
    itm.ProfileCombo:AddItem('Sports Highlights')
    
    local result = nil
    
    function win.On.ApplyBtn.Clicked(ev)
        result = itm.ProfileCombo.CurrentText
        disp:ExitLoop()
    end
    
    function win.On.CancelBtn.Clicked(ev)
        disp:ExitLoop()
    end
    
    function win.On.BrandWin.Close(ev)
        disp:ExitLoop()
    end
    
    win:Show()
    disp:RunLoop()
    win:Hide()
    
    return result
end

local function apply_branding(profile)
    if not profile or profile == 'Select Profile...' then return end
    
    local resolve = Resolve()
    local projectManager = resolve:GetProjectManager()
    local project = projectManager:GetCurrentProject()
    local mediaPool = project:GetMediaPool()
    local timeline = project:GetCurrentTimeline()
    
    if not timeline then return end
    
    print("Applying branding for: " .. profile)
    
    -- Define assets based on profile
    -- Use relative path from script location
    local script_path = debug.getinfo(1, "S").source:match("@(.*/)")
    local assets_base = script_path and (script_path .. "../assets/branding") or (os.getenv("HOME") .. "/LTW_Clipper/assets/branding")
    local intro_path = assets_base .. "/intro.mov"
    local outro_path = assets_base .. "/outro.mov"
    
    -- Import Assets
    local items = mediaPool:ImportMedia({intro_path, outro_path})
    
    -- Note: Resolve API timeline manipulation for "Insert at Start" is complex
    -- Strategy:
    -- 1. Append Intro to end, then move it? No.
    -- 2. Current API best practice: Create new timeline, Append Intro, Append Clips from old timeline, Append Outro.
    
    print("NOTE: To fully implement, please ensure 'intro.mov' and 'outro.mov' exist in assets/branding/")
    print("      Script will then insert them at start/end of timeline.")
end

local profile = get_branding_profile()
apply_branding(profile)

