De GUI_MAIN moet gerund worden voor het activeren van de code
Alle files moeten op exact dezelfde manier als in de repository worden opgeslagen, hier bouwt de code op.
https://downloads.alliedvision.com/Vimba_v6.0_Windows.exe
"C:\Users\jij\.virtualenvs\vimbapython-master\Scripts\python.exe" -m PyInstaller ^
  --onefile ^
  --clean ^
  --hidden-import vimba ^
  --hidden-import vimba.error ^
  --hidden-import vimba.c_binding ^
  --hidden-import vimba.camera ^
  --hidden-import vimba.frame ^
  --paths "C:\pad\naar\VimbaPython" ^
  --add-binary "%VIMBA_HOME%\VimbaC\bin\*.dll;VimbaC\bin" ^
  GUI_main.py
