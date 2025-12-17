-- LTW Universal Import Script
-- Imports a selected folder of media and organizes it into bins
-- Author: LTW Video Editor Pro

local function get_folder_path()
    -- Use UI to ask user for folder path (Simple text input for now as native file pickers are tricky in Lua/Resolve without Fusion UI)
    local ui = fu.UIManager
    local disp = bmd.UIDispatcher(ui)
    
    local win = disp:AddWindow({
        ID = 'MyWin',
        WindowTitle = 'LTW Universal Import',
        Geometry = {100, 100, 400, 120},
        Spacing = 10,
        
        ui:VGroup{
            ui:Label{ID = 'Label', Text = 'Enter full folder path to import:', Weight = 0},
            ui:LineEdit{ID = 'PathInput', Text = '', PlaceholderText = '/Users/yourname/Desktop/clips', Weight = 0},
            ui:HGroup{
                Weight = 0,
                ui:Button{ID = 'ImportBtn', Text = 'Import Folder'},
                ui:Button{ID = 'CancelBtn', Text = 'Cancel'}
            },
            ui:VGap(2)
        }
    })
    
    local itm = win:GetItems()
    local path_to_import = nil
    
    function win.On.ImportBtn.Clicked(ev)
        path_to_import = itm.PathInput.Text
        disp:ExitLoop()
    end
    
    function win.On.CancelBtn.Clicked(ev)
        disp:ExitLoop()
    end
    
    function win.On.MyWin.Close(ev)
        disp:ExitLoop()
    end
    
    win:Show()
    disp:RunLoop()
    win:Hide()
    
    return path_to_import
end

local function process_import(folder_path)
    if not folder_path or folder_path == "" then
        print("No folder selected.")
        return
    end

    local resolve = Resolve()
    local projectManager = resolve:GetProjectManager()
    local project = projectManager:GetCurrentProject()
    
    if not project then
        print("No open project. Please open a project first.")
        return
    end
    
    local mediaPool = project:GetMediaPool()
    local rootFolder = mediaPool:GetRootFolder()
    
    -- Create a bin for this import
    local import_name = string.match(folder_path, "([^/]+)$") or "Imported_Media"
    local newBin = mediaPool:AddSubFolder(rootFolder, import_name)
    mediaPool:SetCurrentFolder(newBin)
    
    print("Importing media from: " .. folder_path)
    
    -- Use OS specific command to list files (Mac/Linux)
    -- Lua in Resolve is limited in file system access, so we use mediaPool:ImportMedia directly on files
    -- However, ImportMedia usually takes a file list or single file.
    -- We can try importing the Folder itself if supported, or we need to scan it.
    -- Resolve's API allows importing a directory structure.
    
    local items = mediaPool:ImportMedia(folder_path)
    
    if items and #items > 0 then
        print("Successfully imported " .. #items .. " items.")
        
        -- Optional: Create a timeline with these clips
        local timelineName = import_name .. "_Timeline"
        local timeline = mediaPool:CreateEmptyTimeline(timelineName)
        
        if timeline then
            mediaPool:AppendToTimeline(items)
            print("Created timeline: " .. timelineName)
        end
    else
        print("No media found or import failed.")
    end
end

-- Run the script
local folder = get_folder_path()
if folder then
    process_import(folder)
end

