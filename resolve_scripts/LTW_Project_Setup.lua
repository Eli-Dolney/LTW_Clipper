-- LTW Project Setup
-- Instantly configure timeline resolution and frame rate for any workflow
-- Author: LTW Video Editor Pro

local function get_project_settings()
    local ui = fu.UIManager
    local disp = bmd.UIDispatcher(ui)
    
    local win = disp:AddWindow({
        ID = 'SetupWin',
        WindowTitle = 'LTW Project Setup',
        Geometry = {100, 100, 350, 250},
        Spacing = 10,
        
        ui:VGroup{
            ui:Label{ID = 'Label1', Text = 'Timeline Resolution:', Weight = 0},
            ui:ComboBox{ID = 'ResCombo', Text = '1920 x 1080 HD'},
            
            ui:Label{ID = 'Label2', Text = 'Frame Rate:', Weight = 0},
            ui:ComboBox{ID = 'FpsCombo', Text = '60 fps'},
            
            ui:Label{ID = 'Label3', Text = 'Scaling:', Weight = 0},
            ui:ComboBox{ID = 'ScaleCombo', Text = 'Scale full frame with crop'},
            
            ui:VGap(10),
            ui:HGroup{
                Weight = 0,
                ui:Button{ID = 'ApplyBtn', Text = 'Apply Settings'},
                ui:Button{ID = 'CancelBtn', Text = 'Cancel'}
            }
        }
    })
    
    local itm = win:GetItems()
    
    -- Resolutions
    itm.ResCombo:AddItem('1920 x 1080 HD')
    itm.ResCombo:AddItem('2560 x 1440 (2K)')
    itm.ResCombo:AddItem('3840 x 2160 UHD (4K)')
    itm.ResCombo:AddItem('1080 x 1920 Vertical (TikTok)')
    itm.ResCombo:AddItem('1080 x 1080 Square (IG)')
    itm.ResCombo:AddItem('1080 x 1350 Portrait (IG 4:5)')
    
    -- Frame Rates
    itm.FpsCombo:AddItem('24 fps')
    itm.FpsCombo:AddItem('30 fps')
    itm.FpsCombo:AddItem('60 fps')
    
    -- Scaling
    itm.ScaleCombo:AddItem('Scale entire image to fit')
    itm.ScaleCombo:AddItem('Scale full frame with crop')
    itm.ScaleCombo:AddItem('Stretch frame to all corners')
    
    local result = nil
    
    function win.On.ApplyBtn.Clicked(ev)
        result = {
            resolution = itm.ResCombo.CurrentText,
            fps = itm.FpsCombo.CurrentText,
            scaling = itm.ScaleCombo.CurrentText
        }
        disp:ExitLoop()
    end
    
    function win.On.CancelBtn.Clicked(ev)
        disp:ExitLoop()
    end
    
    function win.On.SetupWin.Close(ev)
        disp:ExitLoop()
    end
    
    win:Show()
    disp:RunLoop()
    win:Hide()
    
    return result
end

local function apply_settings(settings)
    if not settings then return end
    
    local projectManager = resolve:GetProjectManager()
    local project = projectManager:GetCurrentProject()
    if not project then return end
    
    print("Applying Project Settings...")
    
    -- Parse Resolution
    local width = 1920
    local height = 1080
    
    if settings.resolution == '2560 x 1440 (2K)' then
        width = 2560; height = 1440
    elseif settings.resolution == '3840 x 2160 UHD (4K)' then
        width = 3840; height = 2160
    elseif settings.resolution == '1080 x 1920 Vertical (TikTok)' then
        width = 1080; height = 1920
    elseif settings.resolution == '1080 x 1080 Square (IG)' then
        width = 1080; height = 1080
    elseif settings.resolution == '1080 x 1350 Portrait (IG 4:5)' then
        width = 1080; height = 1350
    end
    
    -- Parse FPS
    local fps = 60
    if settings.fps == '24 fps' then fps = 24
    elseif settings.fps == '30 fps' then fps = 30 end
    
    -- Set Project Settings
    project:SetSetting("timelineResolutionWidth", tostring(width))
    project:SetSetting("timelineResolutionHeight", tostring(height))
    project:SetSetting("timelineFrameRate", tostring(fps))
    project:SetSetting("timelinePlaybackFrameRate", tostring(fps))
    
    -- Scaling
    -- "scaleToFit" = fit, "scaleToFill" = crop
    local scaleMode = "scaleToFit"
    if settings.scaling == 'Scale full frame with crop' then scaleMode = "scaleToFill"
    elseif settings.scaling == 'Stretch frame to all corners' then scaleMode = "scaleToResize" end
    
    project:SetSetting("inputScalingPreset", scaleMode)
    
    print(string.format("✅ Set Resolution: %dx%d @ %d fps", width, height, fps))
    print("✅ Scaling Mode: " .. settings.scaling)
end

local settings = get_project_settings()
apply_settings(settings)

