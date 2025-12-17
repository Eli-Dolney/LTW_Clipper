-- LTW Auto-Transitioner (Interactive Guide)
-- Since Resolve API cannot add transitions directly, we guide the user to the native hotkeys.

local function show_guide(style)
    local ui = fu.UIManager
    local disp = bmd.UIDispatcher(ui)
    
    local win = disp:AddWindow({
        ID = 'GuideWin',
        WindowTitle = 'Apply Transitions',
        Geometry = {100, 100, 400, 200},
        Spacing = 10,
        
        ui:VGroup{
            ui:Label{ID = 'Info', Text = 'DaVinci Resolve API Limitation:', Weight = 0, Font = ui:Font{Family = "Helvetica", PixelSize = 14, Bold = true}},
            ui:Label{ID = 'Info2', Text = 'Scripts cannot currently apply transitions automatically.', Weight = 0},
            ui:VGap(10),
            ui:Label{ID = 'Action', Text = '⚡ BUT YOU CAN DO IT IN 1 SECOND:', Weight = 0, Font = ui:Font{Family = "Helvetica", PixelSize = 14, Bold = true, Color = {1, 1, 0, 1}}},
            ui:HGroup{
                ui:Label{ID = 'Step1', Text = '1. Press Cmd + A (Select All)', Weight = 1},
            },
            ui:HGroup{
                ui:Label{ID = 'Step2', Text = '2. Press Cmd + T (Add ' .. style .. ')', Weight = 1},
            },
            ui:VGap(10),
            ui:HGroup{
                Weight = 0,
                ui:Button{ID = 'OkBtn', Text = 'Got it!'}
            }
        }
    })
    
    local itm = win:GetItems()
    
    function win.On.OkBtn.Clicked(ev)
        disp:ExitLoop()
    end
    
    function win.On.GuideWin.Close(ev)
        disp:ExitLoop()
    end
    
    win:Show()
    disp:RunLoop()
    win:Hide()
end

local function get_transition_settings()
    local ui = fu.UIManager
    local disp = bmd.UIDispatcher(ui)
    
    local win = disp:AddWindow({
        ID = 'TransWin',
        WindowTitle = 'LTW Auto-Transitioner',
        Geometry = {100, 100, 300, 130},
        Spacing = 10,
        
        ui:VGroup{
            ui:Label{ID = 'Label', Text = 'Select Transition Style:', Weight = 0},
            ui:ComboBox{ID = 'StyleCombo', Text = 'Standard Transition'},
            ui:VGap(5),
            ui:HGroup{
                Weight = 0,
                ui:Button{ID = 'ApplyBtn', Text = 'Show Me How'},
                ui:Button{ID = 'CancelBtn', Text = 'Cancel'}
            }
        }
    })
    
    local itm = win:GetItems()
    
    itm.StyleCombo:AddItem('Standard Transition (Cmd+T)')
    
    local result = nil
    
    function win.On.ApplyBtn.Clicked(ev)
        result = itm.StyleCombo.CurrentText
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

-- Run
local style = get_transition_settings()
if style then
    show_guide(style)
end
