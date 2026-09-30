@echo off
REM ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com
REM
REM SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
python -B "%~dp0compiler\c48b2tap.py" %*
exit /b %ERRORLEVEL%
