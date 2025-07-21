Set WshShell = WScript.CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' �� ��ũ��Ʈ�� ����Ǵ� ���� ���丮 (������Ʈ�� ���� �ٱ� ����)
strProjectRoot = WshShell.CurrentDirectory

' �ٷΰ��� ���� ��� ����
strShortcutFolderName = "�ٷΰ���"
strShortcutFolderPath = strProjectRoot & "\" & strShortcutFolderName

' 1. "�ٷΰ���" ���� ���� (�̹� �ִٸ� ������ ����)
If Not fso.FolderExists(strShortcutFolderPath) Then
    fso.CreateFolder strShortcutFolderPath
    WScript.Echo "'" & strShortcutFolderName & "' ������ �����Ǿ����ϴ�: " & strShortcutFolderPath
Else
    WScript.Echo "'" & strShortcutFolderName & "' ������ �̹� �����մϴ�: " & strShortcutFolderPath
End If

' ������ �ٷΰ��� ���: {��� ���ϸ�, �ٷΰ��� �̸�}
Dim arrShortcuts(3, 1)

arrShortcuts(0, 0) = "windows_run.bat"
arrShortcuts(0, 1) = "1.�����ϱ�.lnk"

arrShortcuts(1, 0) = ".env"
arrShortcuts(1, 1) = "2.��������.lnk"

arrShortcuts(2, 0) = "vendor_items.csv"
arrShortcuts(2, 1) = "3.��ǰ���.lnk"

arrShortcuts(3, 0) = "windows_update.bat"
arrShortcuts(3, 1) = "4.������Ʈ.lnk"

' �� �ٷΰ��� ����
For i = 0 To UBound(arrShortcuts, 1)
    strTargetFile = arrShortcuts(i, 0) ' ���� ���� �̸� (��: windows_run.bat)
    strShortcutName = arrShortcuts(i, 1) ' �ٷΰ��� ���� �̸� (��: 1.�����ϱ�.lnk)

    strTargetFullPath = strProjectRoot & "\" & strTargetFile ' ���� ������ ��ü ���
    strShortcutFullPath = strShortcutFolderPath & "\" & strShortcutName ' �ٷΰ��Ⱑ ������ ��ü ���

    ' ���� ������ �����ϴ��� Ȯ�� �� �ٷΰ��� ����
    If fso.FileExists(strTargetFullPath) Then
        Set oShellLink = WshShell.CreateShortcut(strShortcutFullPath)
        oShellLink.TargetPath = strTargetFullPath
        oShellLink.WorkingDirectory = strProjectRoot ' �ٷΰ��� ���� �� �۾� ���丮�� ������Ʈ ��Ʈ�� ����

        ' �ٷΰ��⿡ ���� ����
        Select Case LCase(strTargetFile)
            Case "windows_run.bat"
                oShellLink.Description = "Coupang �ڵ� ���� ���� ���α׷��� �����մϴ�."
            Case ".env"
                oShellLink.Description = "ȯ�� ���� ������ ���ϴ�."
            Case "vendor_items.csv"
                oShellLink.Description = "���� ���� ��ǰ ��� ������ ���ϴ�."
            Case "windows_update.bat"
                oShellLink.Description = "Coupang �ڵ� ���� ���� ���α׷��� �ֽ� �������� ������Ʈ�մϴ�."
        End Select

        ' (���� ����) �ٷΰ��� ������ ����: ���� ������ �´� ������ ����
        Select Case LCase(strTargetFile)
            Case "windows_run.bat", "windows_update.bat"
                oShellLink.IconLocation = "shell32.dll, 2" ' �Ϲ����� ��ġ ���� ������
            Case ".env"
                oShellLink.IconLocation = "shell32.dll, 77" ' �ؽ�Ʈ ���� ������
            Case "vendor_items.csv"
                oShellLink.IconLocation = "imageres.dll, 107" ' CSV/���������Ʈ ������ (Excel�� ��ġ�Ǿ� �ִٸ� Excel �������� ���� �� ����)
        End Select

        oShellLink.Save
        WScript.Echo "'" & strShortcutName & "' �ٷΰ��Ⱑ �����Ǿ����ϴ�."
    Else
        WScript.Echo "���: ��� ������ �������� �ʽ��ϴ� - " & strTargetFile & ". �� ������ �ٷΰ���� �������� �ʾҽ��ϴ�."
    End If
Next

WScript.Echo "��� ��û�� �ٷΰ��� ������ �õ��߽��ϴ�. '�ٷΰ���' ������ Ȯ�����ּ���."

Set oShellLink = Nothing
Set fso = Nothing
Set WshShell = Nothing