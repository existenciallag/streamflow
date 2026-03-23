Attribute VB_Name = "Inventory"
' =============================================================================
' StreamFlow - Inventory Management Module
' =============================================================================
' Functions for managing reagent units (add, edit, change status)
' =============================================================================

Option Explicit

' Add new reagent unit
Sub AddNewUnit()
    Dim reagentName As String
    Dim lot As String
    Dim expirationDate As Date
    Dim arrivalDate As Date
    Dim initialVolume As Double
    Dim currentVolume As Double
    Dim status As String

    ' Show input form
    reagentName = Application.InputBox("Enter Reagent Name (or ID):", "Add New Unit", Type:=2)
    If reagentName = "False" Or reagentName = "" Then Exit Sub

    lot = Application.InputBox("Enter Lot Number:", "Add New Unit", Type:=2)
    If lot = "False" Then Exit Sub

    ' Get dates
    Dim expDateStr As String
    expDateStr = Application.InputBox("Enter Expiration Date (YYYY-MM-DD):", "Add New Unit", Format(Date + 365, "yyyy-mm-dd"), Type:=2)
    If expDateStr = "False" Then Exit Sub
    On Error Resume Next
    expirationDate = CDate(expDateStr)
    If Err.Number <> 0 Then
        MsgBox "Invalid date format. Please use YYYY-MM-DD", vbExclamation
        Exit Sub
    End If
    On Error GoTo 0

    arrivalDate = Date ' Default to today

    ' Get volume
    initialVolume = Application.InputBox("Enter Initial Volume (µL):", "Add New Unit", 100, Type:=1)
    If initialVolume = 0 Then Exit Sub

    currentVolume = initialVolume
    status = "Stored"

    ' Find reagent ID
    Dim reagentID As String
    reagentID = FindReagentID(reagentName)
    If reagentID = "" Then
        MsgBox "Reagent not found: " & reagentName, vbExclamation
        Exit Sub
    End If

    ' Generate new unit ID
    Dim newID As String
    newID = GenerateID()

    ' Add to sheet
    Dim ws As Worksheet
    Set ws = Sheets("Reagent_Units")

    Dim lastRow As Long
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row + 1

    ws.Cells(lastRow, 1).Value = newID
    ws.Cells(lastRow, GetColumnNumber("Reagent_Units", "reagent_id")).Value = reagentID
    ws.Cells(lastRow, GetColumnNumber("Reagent_Units", "lot")).Value = lot
    ws.Cells(lastRow, GetColumnNumber("Reagent_Units", "expiration_date")).Value = expirationDate
    ws.Cells(lastRow, GetColumnNumber("Reagent_Units", "arrival_date")).Value = arrivalDate
    ws.Cells(lastRow, GetColumnNumber("Reagent_Units", "initial_volume")).Value = initialVolume
    ws.Cells(lastRow, GetColumnNumber("Reagent_Units", "current_volume")).Value = currentVolume
    ws.Cells(lastRow, GetColumnNumber("Reagent_Units", "status")).Value = status

    MsgBox "Unit added successfully!" & vbCrLf & "Lot: " & lot, vbInformation

    Call RefreshDashboard
End Sub

' Change unit status
Sub ChangeUnitStatus()
    Dim unitID As String
    Dim newStatus As String

    unitID = Application.InputBox("Enter Unit ID or Lot Number:", "Change Status", Type:=2)
    If unitID = "False" Or unitID = "" Then Exit Sub

    ' Find unit
    Dim ws As Worksheet
    Set ws = Sheets("Reagent_Units")

    Dim lastRow As Long
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    Dim i As Long
    Dim foundRow As Long
    foundRow = 0

    For i = 2 To lastRow
        If ws.Cells(i, 1).Value = unitID Or _
           ws.Cells(i, GetColumnNumber("Reagent_Units", "lot")).Value = unitID Then
            foundRow = i
            Exit For
        End If
    Next i

    If foundRow = 0 Then
        MsgBox "Unit not found: " & unitID, vbExclamation
        Exit Sub
    End If

    ' Show status options
    Dim result As Integer
    result = MsgBox("Select new status:" & vbCrLf & vbCrLf & _
                    "YES = In Use" & vbCrLf & _
                    "NO = Stored" & vbCrLf & _
                    "CANCEL = Empty", _
                    vbYesNoCancel + vbQuestion, "Change Status")

    Select Case result
        Case vbYes
            newStatus = "In Use"
        Case vbNo
            newStatus = "Stored"
        Case vbCancel
            newStatus = "Empty"
        Case Else
            Exit Sub
    End Select

    ' Update status
    ws.Cells(foundRow, GetColumnNumber("Reagent_Units", "status")).Value = newStatus

    MsgBox "Status updated to: " & newStatus, vbInformation

    Call RefreshDashboard
End Sub

' Register usage (decrease volume)
Sub RegisterUsage()
    Dim unitID As String
    Dim usedVolume As Double

    unitID = Application.InputBox("Enter Unit ID or Lot Number:", "Register Usage", Type:=2)
    If unitID = "False" Or unitID = "" Then Exit Sub

    usedVolume = Application.InputBox("Enter Volume Used (µL):", "Register Usage", 5, Type:=1)
    If usedVolume = 0 Then Exit Sub

    ' Find unit
    Dim ws As Worksheet
    Set ws = Sheets("Reagent_Units")

    Dim lastRow As Long
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    Dim i As Long
    Dim foundRow As Long
    foundRow = 0

    For i = 2 To lastRow
        If ws.Cells(i, 1).Value = unitID Or _
           ws.Cells(i, GetColumnNumber("Reagent_Units", "lot")).Value = unitID Then
            foundRow = i
            Exit For
        End If
    Next i

    If foundRow = 0 Then
        MsgBox "Unit not found: " & unitID, vbExclamation
        Exit Sub
    End If

    ' Update volume
    Dim currentVol As Double
    currentVol = ws.Cells(foundRow, GetColumnNumber("Reagent_Units", "current_volume")).Value
    currentVol = currentVol - usedVolume

    If currentVol < 0 Then currentVol = 0

    ws.Cells(foundRow, GetColumnNumber("Reagent_Units", "current_volume")).Value = currentVol

    ' Auto-update status
    If currentVol = 0 Then
        ws.Cells(foundRow, GetColumnNumber("Reagent_Units", "status")).Value = "Empty"
        MsgBox "Volume updated. Unit is now Empty.", vbInformation
    Else
        ws.Cells(foundRow, GetColumnNumber("Reagent_Units", "status")).Value = "In Use"
        MsgBox "Volume updated. Remaining: " & currentVol & " µL", vbInformation
    End If

    Call RefreshDashboard
End Sub

' Helper: Find reagent ID by name
Function FindReagentID(reagentName As String) As String
    Dim ws As Worksheet
    Set ws = Sheets("Reagents")

    Dim lastRow As Long
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    Dim nameCol As Long
    nameCol = GetColumnNumber("Reagents", "name")

    Dim i As Long
    For i = 2 To lastRow
        If LCase(Trim(ws.Cells(i, nameCol).Value)) = LCase(Trim(reagentName)) Then
            FindReagentID = ws.Cells(i, 1).Value
            Exit Function
        End If
    Next i

    ' Try by ID
    For i = 2 To lastRow
        If ws.Cells(i, 1).Value = reagentName Then
            FindReagentID = ws.Cells(i, 1).Value
            Exit Function
        End If
    Next i

    FindReagentID = ""
End Function

' Helper: Generate unique ID
Function GenerateID() As String
    GenerateID = "UNIT-" & Format(Now, "yyyymmddhhnnss") & "-" & Int(Rnd * 1000)
End Function
