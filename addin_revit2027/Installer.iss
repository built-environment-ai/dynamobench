[Setup]
AppName=DynamoBench for Revit 2027
AppVersion=0.1.0
AppPublisher=Built Environment AI Initiative
AppPublisherURL=https://built-environment-ai.org
DefaultDirName={userappdata}\Autodesk\Revit\Addins\2027
DisableDirPage=yes
DefaultGroupName=DynamoBench
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=DynamoBench_Revit2027_Setup_v0.1.0
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "DynamoBench_Revit2027_Addin\DynamoBench.Revit2027.addin"; DestDir: "{app}"; Flags: ignoreversion
Source: "DynamoBench_Revit2027_Addin\DynamoBench.Revit2027.dll"; DestDir: "{app}"; Flags: ignoreversion
