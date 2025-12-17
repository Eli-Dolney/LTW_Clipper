-- LTW Quick Render
-- One-click setup for YouTube, Social Media, and Master renders
-- Author: LTW Video Editor Pro

local function get_render_settings()
    local ui = fu.UIManager
    local disp = bmd.UIDispatcher(ui)
    
    local win = disp:AddWindow({
        ID = 'RenderWin',
        WindowTitle = 'LTW Quick Render',
        Geometry = {100, 100, 400, 200},
        Spacing = 10,
        
        ui:VGroup{
            ui:Label{ID = 'Label', Text = 'Select Render Preset:', Weight = 0},
            ui:ComboBox{ID = 'PresetCombo', Text = 'YouTube 4K (H.264)'},
            
            ui:Label{ID = 'DestLabel', Text = 'Output Location:', Weight = 0},
            ui:ComboBox{ID = 'DestCombo', Text = 'Desktop'},
            
            ui:Label{ID = 'QueueLabel', Text = 'Action:', Weight = 0},
            ui:ComboBox{ID = 'QueueCombo', Text = 'Add to Render Queue'},
            
            ui:VGap(10),
            ui:HGroup{
                Weight = 0,
                ui:Button{ID = 'RenderBtn', Text = 'Setup Render'},
                ui:Button{ID = 'CancelBtn', Text = 'Cancel'}
            }
        }
    })
    
    local itm = win:GetItems()
    
    -- Presets
    itm.PresetCombo:AddItem('YouTube 4K (H.264)')
    itm.PresetCombo:AddItem('YouTube 1080p (H.264)')
    itm.PresetCombo:AddItem('Social Vertical (1080x1920)')
    itm.PresetCombo:AddItem('Master ProRes 422 HQ')
    
    -- Destinations
    itm.DestCombo:AddItem('Desktop')
    itm.DestCombo:AddItem('Movies')
    itm.DestCombo:AddItem('Source Folder')
    
    -- Actions
    itm.QueueCombo:AddItem('Add to Render Queue')
    itm.QueueCombo:AddItem('Add & Start Rendering')
    
    local result = nil
    
    function win.On.RenderBtn.Clicked(ev)
        result = {
            preset = itm.PresetCombo.CurrentText,
            destination = itm.DestCombo.CurrentText,
            action = itm.QueueCombo.CurrentText
        }
        disp:ExitLoop()
    end
    
    function win.On.CancelBtn.Clicked(ev)
        disp:ExitLoop()
    end
    
    function win.On.RenderWin.Close(ev)
        disp:ExitLoop()
    end
    
    win:Show()
    disp:RunLoop()
    win:Hide()
    
    return result
end

local function setup_render(settings)
    if not settings then return end
    
    local resolve = Resolve()
    local projectManager = resolve:GetProjectManager()
    local project = projectManager:GetCurrentProject()
    if not project then return end
    
    print("Setting up render: " .. settings.preset)
    
    -- Clear existing render settings
    project:DeleteAllRenderJobs()
    
    -- Determine Output Path
    local home = os.getenv("HOME")
    local target_dir = home .. "/Desktop/Render_Output"
    
    if settings.destination == 'Movies' then
        target_dir = home .. "/Movies/Render_Output"
    end
    
    -- Determine Settings based on Preset
    if settings.preset == 'YouTube 4K (H.264)' then
        project:SetCurrentRenderFormatAndCodec("mp4", "H264")
        project:SetRenderSettings({
            Width = 3840,
            Height = 2160,
            TargetDir = target_dir,
            CustomName = project:GetName() .. "_4K"
        })
    elseif settings.preset == 'YouTube 1080p (H.264)' then
        project:SetCurrentRenderFormatAndCodec("mp4", "H264")
        project:SetRenderSettings({
            Width = 1920,
            Height = 1080,
            TargetDir = target_dir,
            CustomName = project:GetName() .. "_1080p"
        })
    elseif settings.preset == 'Social Vertical (1080x1920)' then
        project:SetCurrentRenderFormatAndCodec("mp4", "H264")
        project:SetRenderSettings({
            Width = 1080,
            Height = 1920,
            TargetDir = target_dir,
            CustomName = project:GetName() .. "_Short"
        })
    elseif settings.preset == 'Master ProRes 422 HQ' then
        project:SetCurrentRenderFormatAndCodec("mov", "ProRes422HQ")
        project:SetRenderSettings({
            TargetDir = target_dir,
            CustomName = project:GetName() .. "_Master"
        })
    end
    
    -- Add to Queue
    project:AddRenderJob()
    
    print("Added to Render Queue at: " .. target_dir)
    
    if settings.action == 'Add & Start Rendering' then
        print("Starting Render...")
        project:StartRendering()
    else
        print("Ready to render! Go to Deliver page to verify.")
    end
end

local settings = get_render_settings()
setup_render(settings)

