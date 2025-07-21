Set WshShell = WScript.CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' 이 스크립트가 실행되는 현재 디렉토리 (프로젝트의 가장 바깥 폴더)
strProjectRoot = WshShell.CurrentDirectory

' 바로가기 폴더 경로 설정
strShortcutFolderName = "바로가기"
strShortcutFolderPath = strProjectRoot & "\" & strShortcutFolderName

' 1. "바로가기" 폴더 생성 (이미 있다면 만들지 않음)
If Not fso.FolderExists(strShortcutFolderPath) Then
    fso.CreateFolder strShortcutFolderPath
    WScript.Echo "'" & strShortcutFolderName & "' 폴더가 생성되었습니다: " & strShortcutFolderPath
Else
    WScript.Echo "'" & strShortcutFolderName & "' 폴더가 이미 존재합니다: " & strShortcutFolderPath
End If

' 생성할 바로가기 목록: {대상 파일명, 바로가기 이름}
Dim arrShortcuts(3, 1)

arrShortcuts(0, 0) = "windows_run.bat"
arrShortcuts(0, 1) = "1.실행하기.lnk"

arrShortcuts(1, 0) = ".env"
arrShortcuts(1, 1) = "2.설정편집.lnk"

arrShortcuts(2, 0) = "vendor_items.csv"
arrShortcuts(2, 1) = "3.상품목록.lnk"

arrShortcuts(3, 0) = "windows_update.bat"
arrShortcuts(3, 1) = "4.업데이트.lnk"

' 각 바로가기 생성
For i = 0 To UBound(arrShortcuts, 1)
    strTargetFile = arrShortcuts(i, 0) ' 원본 파일 이름 (예: windows_run.bat)
    strShortcutName = arrShortcuts(i, 1) ' 바로가기 파일 이름 (예: 1.실행하기.lnk)

    strTargetFullPath = strProjectRoot & "\" & strTargetFile ' 원본 파일의 전체 경로
    strShortcutFullPath = strShortcutFolderPath & "\" & strShortcutName ' 바로가기가 생성될 전체 경로

    ' *** 파일 존재 여부 확인 로직 제거: 이제 파일이 없어도 바로가기가 생성됩니다. ***

    Set oShellLink = WshShell.CreateShortcut(strShortcutFullPath)
    oShellLink.TargetPath = strTargetFullPath
    oShellLink.WorkingDirectory = strProjectRoot ' 바로가기 실행 시 작업 디렉토리는 프로젝트 루트로 설정

    ' 바로가기에 대한 설명
    Select Case LCase(strTargetFile)
        Case "windows_run.bat"
            oShellLink.Description = "Coupang 자동 쿠폰 관리 프로그램을 실행합니다."
        Case ".env"
            oShellLink.Description = "환경 설정 파일을 엽니다."
        Case "vendor_items.csv"
            oShellLink.Description = "쿠폰 적용 상품 목록 파일을 엽니다."
        Case "windows_update.bat"
            oShellLink.Description = "Coupang 자동 쿠폰 관리 프로그램을 최신 버전으로 업데이트합니다."
    End Select

    ' (선택 사항) 바로가기 아이콘 설정: 파일 종류에 맞는 아이콘 지정
    Select Case LCase(strTargetFile)
        Case "windows_run.bat", "windows_update.bat"
            oShellLink.IconLocation = "shell32.dll, 2" ' 일반적인 배치 파일 아이콘
        Case ".env"
            oShellLink.IconLocation = "shell32.dll, 77" ' 텍스트 파일 아이콘
        Case "vendor_items.csv"
            oShellLink.IconLocation = "imageres.dll, 107" ' CSV/스프레드시트 아이콘 (Excel이 설치되어 있다면 Excel 아이콘이 나올 수 있음)
    End Select

    oShellLink.Save
    WScript.Echo "'" & strShortcutName & "' 바로가기가 생성되었습니다."
Next

WScript.Echo "모든 요청된 바로가기 생성을 시도했습니다. '바로가기' 폴더를 확인해주세요."

Set oShellLink = Nothing
Set fso = Nothing
Set WshShell = Nothing