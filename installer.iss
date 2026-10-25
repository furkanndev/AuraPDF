; Inno Setup Kurulum Senaryosu
; AuraPDF (Setup Installer)

#define MyAppName "AuraPDF"
#define MyAppFullName "AuraPDF"
#ifndef MyAppVersion
#define MyAppVersion "Pro v2.2.3"
#endif
#ifndef OutputFileName
#define OutputFileName "AuraPDF_Pro v2.2.3"
#endif
#ifndef OutputDir
#define OutputDir "Kurulum\Pro"
#endif
#define MyAppPublisher "AuraPDF"
#define MyAppExeName "AuraPDF.exe"
#ifndef MyAppIcon
#define MyAppIcon "app_icon.ico"
#endif
#define MyDistDir "dist\AuraPDF"

[Setup]
AppId={{D9837B55-4601-44B9-A6BE-C67B54DAFE7C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
UninstallDisplayName={#MyAppName}
AppPublisher={#MyAppPublisher}
DefaultDirName={commonpf}\{#MyAppName}
DefaultGroupName={#MyAppFullName}
DisableDirPage=no
UsePreviousAppDir=no
AlwaysShowDirOnReadyPage=yes
AllowNoIcons=yes
OutputDir={#OutputDir}
OutputBaseFilename={#OutputFileName}
SetupIconFile={#MyAppIcon}
UninstallDisplayIcon={app}\app_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
ChangesAssociations=yes

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
turkish.AssocPdf=PDF dosyalarını varsayılan olarak AuraPDF ile ilişkilendir
english.AssocPdf=Associate PDF files with AuraPDF by default
turkish.FileAssociations=Dosya İlişkilendirmeleri:
english.FileAssociations=File Associations:
turkish.UninstallApp=AuraPDF Kaldır
english.UninstallApp=Uninstall AuraPDF
turkish.PdfDocType=PDF Belgesi
english.PdfDocType=PDF Document

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "assocpdf"; Description: "{cm:AssocPdf}"; GroupDescription: "{cm:FileAssociations}"

[Files]
Source: "{#MyAppIcon}"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\pdf_file.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\PdfThumbnailProvider.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\PowerToys.PdfThumbnailProvider.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyDistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppFullName}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"
Name: "{autoprograms}\{#MyAppFullName}\{cm:UninstallApp}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"; Tasks: desktopicon

[Registry]
; PDF Dosya Iliskilendirmesi
Root: HKA; Subkey: "Software\Classes\.pdf\OpenWithProgids"; ValueType: string; ValueName: "AuraPDF.AssocFile.PDF"; ValueData: ""; Flags: uninsdeletevalue; Tasks: assocpdf
Root: HKA; Subkey: "Software\Classes\AuraPDF.AssocFile.PDF"; ValueType: string; ValueName: ""; ValueData: "{cm:PdfDocType}"; Flags: uninsdeletekey; Tasks: assocpdf
Root: HKA; Subkey: "Software\Classes\AuraPDF.AssocFile.PDF\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\pdf_file.ico,0"; Tasks: assocpdf
Root: HKA; Subkey: "Software\Classes\AuraPDF.AssocFile.PDF\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: assocpdf
Root: HKA; Subkey: "Software\Classes\AuraPDF.AssocFile.PDF\ShellEx\{{8895b1c6-b41f-4c1c-a562-0d564250836f}"; ValueType: string; ValueName: ""; ValueData: "{{3A84F9C2-6164-485C-A7D9-4B27F8AC009E}"; Tasks: assocpdf
; PDF Onizleme (Thumbnail Provider) ve Sag-Alt AuraPDF Logo Rozeti
Root: HKA; Subkey: "Software\Classes\CLSID\{{D8BB9942-93BD-412D-87E4-33FAB214DC1A}"; ValueType: string; ValueName: ""; ValueData: "AuraPDF Thumbnail Provider"; Flags: uninsdeletekey; Tasks: assocpdf
Root: HKA; Subkey: "Software\Classes\CLSID\{{D8BB9942-93BD-412D-87E4-33FAB214DC1A}"; ValueType: dword; ValueName: "DisableProcessIsolation"; ValueData: "1"; Tasks: assocpdf
Root: HKA; Subkey: "Software\Classes\CLSID\{{D8BB9942-93BD-412D-87E4-33FAB214DC1A}\InprocServer32"; ValueType: string; ValueName: ""; ValueData: "{app}\PdfThumbnailProvider.dll"; Tasks: assocpdf
Root: HKA; Subkey: "Software\Classes\CLSID\{{D8BB9942-93BD-412D-87E4-33FAB214DC1A}\InprocServer32"; ValueType: string; ValueName: "ThreadingModel"; ValueData: "Apartment"; Tasks: assocpdf
Root: HKA; Subkey: "Software\Classes\AuraPDF.AssocFile.PDF\ShellEx\{{e357fccd-a995-4576-b01f-234630154e96}"; ValueType: string; ValueName: ""; ValueData: "{{D8BB9942-93BD-412D-87E4-33FAB214DC1A}"; Tasks: assocpdf
Root: HKA; Subkey: "Software\Classes\.pdf\ShellEx\{{e357fccd-a995-4576-b01f-234630154e96}"; ValueType: string; ValueName: ""; ValueData: "{{D8BB9942-93BD-412D-87E4-33FAB214DC1A}"; Tasks: assocpdf
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pdf\ShellEx\{{e357fccd-a995-4576-b01f-234630154e96}"; ValueType: string; ValueName: ""; ValueData: "{{D8BB9942-93BD-412D-87E4-33FAB214DC1A}"; Tasks: assocpdf
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"; ValueType: dword; ValueName: "ShowTypeOverlay"; ValueData: "1"; Tasks: assocpdf
; Windows Birlikte Ac (Open With) ve Uygulama Kaydi
Root: HKA; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".pdf"; ValueData: ""; Flags: uninsdeletevalue; Tasks: assocpdf
Root: HKA; Subkey: "Software\Classes\Applications\{#MyAppExeName}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: assocpdf

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
