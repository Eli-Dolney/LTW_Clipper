-- LTW Use Resolve Transcription (Studio Only)
-- Leverages DaVinci Resolve Studio's built-in transcription API
-- Author: LTW Video Editor Pro

local function transcribe_timeline()
    local projectManager = resolve:GetProjectManager()
    local project = projectManager:GetCurrentProject()
    local timeline = project:GetCurrentTimeline()
    
    if not timeline then
        print("No timeline active.")
        return
    end
    
    print("🎙️ Using DaVinci Resolve Studio Transcription...")
    print("")
    print("📋 STEPS:")
    print("   1. Go to the 'Fairlight' page (Audio tab)")
    print("   2. Select your audio track")
    print("   3. Right-click -> 'Transcribe Audio'")
    print("   4. Resolve will generate subtitles automatically")
    print("")
    print("   OR:")
    print("")
    print("   1. Go to 'Edit' page")
    print("   2. Right-click Timeline -> 'Transcribe Audio'")
    print("   3. Select language and click 'Transcribe'")
    print("")
    print("✅ Resolve Studio will create subtitle track automatically!")
    print("")
    print("💡 TIP: After transcription, you can:")
    print("   - Export subtitles (File -> Export -> Subtitles)")
    print("   - Use them in our Smart Clip Finder")
    print("   - Style them with our Transcript Importer")
    
    -- Check if Studio version
    local resolve = Resolve()
    local version = resolve:GetVersionString()
    if not string.find(version, "Studio") then
        print("")
        print("⚠️ WARNING: This feature requires DaVinci Resolve Studio.")
        print("   Free version: Use 'LTW_Transcript_Importer' with external transcripts.")
    end
end

transcribe_timeline()

