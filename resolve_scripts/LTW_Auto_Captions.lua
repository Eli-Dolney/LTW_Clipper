-- LTW Auto Captions
-- Imports captions.srt from an LTW clip bundle into the current timeline.
-- Author: LTW Video Splitter Pro

local function pick_srt()
    local ui = fu.UIManager
    local disp = bmd.UIDispatcher(ui)
    local win = disp:AddWindow({
        ID = 'SrtWin',
        WindowTitle = 'LTW Import Captions',
        Geometry = {100, 100, 500, 100},
        ui:VGroup{
            ui:Label{Text = 'Path to captions.srt (from LTW clip folder):'},
            ui:LineEdit{ID = 'Path', PlaceholderText = '/path/to/clips/slug/captions.srt'},
            ui:Button{ID = 'Import', Text = 'Import SRT'},
        },
    })
    local itm = win:GetItems()
    local result = nil
    function win.On.Import.Clicked(ev)
        result = itm.Path.Text
        disp:ExitLoop()
    end
    function win.On.SrtWin.Close(ev) disp:ExitLoop() end
    win:Show()
    disp:RunLoop()
    win:Hide()
    return result
end

local srt_path = pick_srt()
if not srt_path or srt_path == "" then return end

local f = io.open(srt_path, "r")
if not f then
    print("Could not open: " .. srt_path)
    return
end
local srt = f:read("*a")
f:close()

local resolve = Resolve()
local project = resolve:GetProjectManager():GetCurrentProject()
if not project then
    print("Open a Resolve project first.")
    return
end

local timeline = project:GetCurrentTimeline()
if not timeline then
    print("Open a timeline first.")
    return
end

-- Resolve 18+ can import subtitles via media pool; fallback: log instructions.
local mp = project:GetMediaPool()
local ok = false
if mp.ImportMedia then
    ok = mp:ImportMedia({srt_path})
end

if ok then
    print("LTW: imported " .. srt_path)
else
    print("LTW: add subtitles manually — File > Import > Subtitle, or drag SRT into Media Pool.")
    print("SRT path: " .. srt_path)
end
