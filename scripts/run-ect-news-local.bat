@echo off
REM ============================================================
REM  ECT News Agent — Local Cron Runner (Windows Task Scheduler)
REM ============================================================
REM  Runs the ECT daily news agent from local PC (Thai IP → no 403)
REM  then auto-commits + pushes results to GitHub Pages.
REM
REM  Setup (one time):
REM    1. Open Task Scheduler (taskschd.msc)
REM    2. Create Basic Task: "ECT News Agent - 07:00"
REM    3. Trigger: Daily, 07:00
REM    4. Action: Start a Program
REM       Program: C:\Users\thund\thundthornthep-ai.github.io\scripts\run-ect-news-local.bat
REM    5. Repeat for 11:00 and 15:00
REM
REM  Or (faster): use PowerShell to register all 3 tasks at once:
REM    See scripts/install-ect-cron.ps1
REM
REM  Manual test:
REM    Double-click this file from Explorer, or run from cmd
REM ============================================================

cd /d "C:\Users\thund\thundthornthep-ai.github.io"

echo.
echo ============================================================
echo   ECT News Agent — %DATE% %TIME%
echo ============================================================

REM Pull latest to avoid conflicts with parallel AI sessions
git pull --rebase origin main

REM Run the agent (try live scrape, fall back to seed)
python -X utf8 scripts\ect-news-agent.py --limit 5

IF %ERRORLEVEL% NEQ 0 (
  echo [ERROR] Agent script failed with code %ERRORLEVEL%
  exit /b %ERRORLEVEL%
)

REM Stage only the data files (not PDFs — they're gitignored)
git add blog/bkk-council/data/ect-news/latest.json blog/bkk-council/data/ect-news/images/

REM Check if there's anything to commit
git diff --cached --quiet
IF %ERRORLEVEL% EQU 0 (
  echo [INFO] No changes to commit
  exit /b 0
)

REM Commit + push
git commit -m "chore(ect-news): local auto-update %DATE% %TIME%"
git push origin main

echo.
echo ============================================================
echo   Done. Widget will reflect new data on next page load.
echo ============================================================
exit /b 0
