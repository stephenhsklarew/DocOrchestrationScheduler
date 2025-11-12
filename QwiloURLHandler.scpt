on open location this_URL
	-- Parse the URL
	-- Format: qwilo://action?params
	set urlText to this_URL as text

	-- Remove the scheme
	set urlNoScheme to text 9 thru -1 of urlText -- Remove "qwilo://"

	-- Extract action
	set AppleScript's text item delimiters to "?"
	set urlParts to text items of urlNoScheme
	set actionName to item 1 of urlParts

	-- Extract session ID from parameters
	if (count of urlParts) > 1 then
		set params to item 2 of urlParts
		set AppleScript's text item delimiters to "="
		set paramParts to text items of params
		if (count of paramParts) > 1 then
			set sessionId to item 2 of paramParts
		else
			set sessionId to ""
		end if
	else
		set sessionId to ""
	end if

	set AppleScript's text item delimiters to ""

	-- Handle the action
	if actionName is "review-ideas" then
		-- Create a temporary script to open Terminal with the command
		set orchestratorDir to (POSIX path of (path to home folder)) & "Development/Scripts/DocOrchestrationScheduler"
		set cmdToRun to "cd '" & orchestratorDir & "' && python3 ../DocOrchestrator/orchestrator.py --review --session " & sessionId
		set tempScript to (POSIX path of (path to home folder)) & ".qwilo_temp_cmd.sh"

		-- Write command to temp file
		do shell script "echo " & quoted form of ("#!/bin/bash\n" & cmdToRun) & " > " & quoted form of tempScript
		do shell script "chmod +x " & quoted form of tempScript

		-- Open Terminal with the command using open command (no automation permission needed)
		do shell script "open -a Terminal " & quoted form of tempScript

	else if actionName is "view-documents" then
		-- Open Finder to the output directory
		set outputPath to (POSIX path of (path to home folder)) & "Development/Scripts/DocOrchestrationScheduler/output"
		do shell script "open " & quoted form of outputPath

	else
		display notification "Unknown action: " & actionName with title "Qwilo"
	end if
end open location
