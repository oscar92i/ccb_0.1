; CalmCircleBreath Windows Installer
[Setup]
AppName=CalmCircleBreath
AppVersion=1.0
AppPublisher=YourName
DefaultDirName={pf}\CalmCircleBreath
DefaultGroupName=CalmCircleBreath
UninstallDisplayIcon={app}\assets\logo.ico
OutputDir=dist_installer
OutputBaseFilename=CalmCircleBreath_Setup
Compression=lzma
SolidCompression=yes
SetupIconFile=assets\logo.ico

[Files]
Source: "dist\CalmCircleBreath.exe"; DestDir: "{app}"
Source: "assets\*"; DestDir: "{app}\assets"; Flags: recursesubdirs
Source: "sounds\*"; DestDir: "{app}\sounds"; Flags: recursesubdirs

[Icons]
Name: "{group}\CalmCircleBreath"; Filename: "{app}\CalmCircleBreath.exe"; IconFilename: "{app}\assets\logo.ico"
Name: "{commondesktop}\CalmCircleBreath"; Filename: "{app}\CalmCircleBreath.exe"; IconFilename: "{app}\assets\logo.ico"

[UninstallDelete]
Type: filesandordirs; Name: "{app}"