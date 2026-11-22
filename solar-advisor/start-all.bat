@echo off
rem Starts the three SolarAdvisor services in their own windows, then opens the app.
rem MongoDB must already be running (it runs as a Windows service).
cd /d "%~dp0"
rem Windows' own tools (Git Bash has different programs with the same names)
rem (ping waits about 2 seconds; unlike timeout it also works without a console window)
set "PING=%SystemRoot%\System32\PING.EXE"
set "CURL=%SystemRoot%\System32\curl.exe"

start "SolarAdvisor ML (8000)" cmd /k "cd ml-service && venv\Scripts\python -m uvicorn main:app --reload --port 8000"
start "SolarAdvisor server (5000)" cmd /k "cd server && npm run dev"
start "SolarAdvisor web (5173)" cmd /k "cd client && npm run dev"

rem Open the browser only when the ML service answers (it is the slowest to start), at most about 60 seconds
echo Waiting for the ML service to start (usually 10 to 20 seconds)...
set /a tries=0
:wait
set /a tries+=1
"%CURL%" -s -o nul http://localhost:8000/health && goto ready
if %tries% geq 30 goto slow
"%PING%" -n 3 127.0.0.1 >nul
goto wait

:ready
echo.
echo ML service is ready. Opening the app: http://localhost:5173
"%PING%" -n 3 127.0.0.1 >nul
start "" http://localhost:5173
goto end

:slow
echo.
echo The ML service has not answered after about a minute.
echo Look at the "SolarAdvisor ML (8000)" window for a red error message.
echo Opening the app anyway: http://localhost:5173
start "" http://localhost:5173

:end
echo You can close this window. Keep the three SolarAdvisor windows open while you use the app.
