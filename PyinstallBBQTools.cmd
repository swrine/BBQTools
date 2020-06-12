@echo off

set pyinstaller_dist_path=dist\BBQTools


rmdir /s /q dist

pyinstaller --noconsole --icon=resources/BBQTools.ico BBQTools.py

mkdir %pyinstaller_dist_path%\resources
xcopy /s /y /i "resources" %pyinstaller_dist_path%\resources
xcopy /s /y /i "oraclientdlls" %pyinstaller_dist_path%
for %%F in (config.yaml trmasterdata.json cfmasterdata.csv RunBBQToolsWithPath.cmd) do xcopy /y /i %%F %pyinstaller_dist_path%

@echo on