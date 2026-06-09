-- LTW Import Clip Plan
-- Reads plan.json + per-clip metadata.json and builds a timeline with markers.
-- Author: LTW Video Splitter Pro

local function pick_file(title, placeholder)
    local ui = fu.UIManager
    local disp = bmd.UIDispatcher(ui)
    local win = disp:AddWindow({
        ID = 'PickWin',
        WindowTitle = title,
        Geometry = {100, 100, 500, 120},
        ui:VGroup{
            ui:Label{Text = placeholder},
            ui:LineEdit{ID = 'Path', PlaceholderText = placeholder},
            ui:HGroup{
                ui:Button{ID = 'Ok', Text = 'OK'},
                ui:Button{ID = 'Cancel', Text = 'Cancel'},
            },
        },
    })
    local itm = win:GetItems()
    local result = nil
    function win.On.Ok.Clicked(ev)
        result = itm.Path.Text
        disp:ExitLoop()
    end
    function win.On.Cancel.Clicked(ev) disp:ExitLoop() end
    function win.On.PickWin.Close(ev) disp:ExitLoop() end
    win:Show()
    disp:RunLoop()
    win:Hide()
    return result
end

local function read_file(path)
    local f = io.open(path, "r")
    if not f then return nil end
    local content = f:read("*a")
    f:close()
    return content
end

local plan_path = pick_file("Import Clip Plan", "/path/to/project/plan.json")
if not plan_path or plan_path == "" then return end

local plan_json = read_file(plan_path)
if not plan_json then
    print("Could not read plan: " .. plan_path)
    return
end

local resolve = Resolve()
local pm = resolve:GetProjectManager()
local project = pm:GetCurrentProject()
if not project then
    print("Open a project in Resolve first.")
    return
end

local mp = project:GetMediaPool()
local root = mp:GetRootFolder()

-- Create bin for LTW import
local bin = mp:AddSubFolder(root, "LTW_Clip_Plan")
if not bin then bin = root end

local timeline = project:GetCurrentTimeline()
if not timeline then
    print("Create or open a timeline, then re-run.")
    return
end

local clip_count = 0
for start_s, end_s, title in string.gmatch(plan_json, '"start":%s*([%d%.]+).-"end":%s*([%d%.]+).-"title":%s*"([^"]*)"') do
    local start_f = math.floor(tonumber(start_s) * 24)
    local end_f = math.floor(tonumber(end_s) * 24)
    timeline:AddMarker(start_f, "Blue", title, "", 1)
    clip_count = clip_count + 1
end

print(string.format("LTW: imported %d clip markers from plan.", clip_count))
