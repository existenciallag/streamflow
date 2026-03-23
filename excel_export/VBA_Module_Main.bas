Attribute VB_Name = "Main"
' =============================================================================
' StreamFlow - Main Module
' =============================================================================
' Main entry point and dashboard management
' =============================================================================

Option Explicit

' Initialize the workbook on open
Sub Auto_Open()
    Application.ScreenUpdating = False

    ' Set up dashboard
    Call RefreshDashboard

    ' Navigate to dashboard
    Sheets("Dashboard").Select
    Range("A1").Select

    Application.ScreenUpdating = True

    MsgBox "Welcome to StreamFlow Inventory Manager!" & vbCrLf & vbCrLf & _
           "📊 View Dashboard for summary" & vbCrLf & _
           "📦 Manage inventory from menu buttons" & vbCrLf & _
           "🔬 Create panels and track usage", _
           vbInformation, "StreamFlow"
End Sub

' Refresh all dashboard metrics
Sub RefreshDashboard()
    Application.ScreenUpdating = False

    Dim ws As Worksheet
    Set ws = Sheets("Dashboard")

    ' Calculate metrics
    Dim totalReagents As Long
    Dim totalUnits As Long
    Dim unitsInUse As Long
    Dim unitsStored As Long
    Dim unitsEmpty As Long
    Dim expiringUnits As Long
    Dim expiredUnits As Long

    totalReagents = Application.WorksheetFunction.CountA(Sheets("Reagents").Range("A:A")) - 1
    totalUnits = Application.WorksheetFunction.CountA(Sheets("Reagent_Units").Range("A:A")) - 1

    ' Count by status
    Dim lastRow As Long
    lastRow = Sheets("Reagent_Units").Cells(Sheets("Reagent_Units").Rows.Count, "A").End(xlUp).Row

    Dim i As Long
    Dim status As String
    Dim expirationDate As Date
    Dim today As Date
    today = Date

    For i = 2 To lastRow
        status = Trim(Sheets("Reagent_Units").Cells(i, GetColumnNumber("Reagent_Units", "status")))

        If UCase(status) = "IN USE" Then
            unitsInUse = unitsInUse + 1
        ElseIf UCase(status) = "STORED" Then
            unitsStored = unitsStored + 1
        ElseIf UCase(status) = "EMPTY" Then
            unitsEmpty = unitsEmpty + 1
        End If

        ' Check expiration
        On Error Resume Next
        expirationDate = Sheets("Reagent_Units").Cells(i, GetColumnNumber("Reagent_Units", "expiration_date"))
        If Err.Number = 0 And expirationDate > 0 Then
            If expirationDate < today Then
                expiredUnits = expiredUnits + 1
            ElseIf expirationDate <= today + 30 Then
                expiringUnits = expiringUnits + 1
            End If
        End If
        On Error GoTo 0
    Next i

    ' Update dashboard cells
    ws.Range("B2").Value = totalReagents
    ws.Range("B3").Value = totalUnits
    ws.Range("B4").Value = unitsInUse
    ws.Range("B5").Value = unitsStored
    ws.Range("B6").Value = unitsEmpty
    ws.Range("B7").Value = expiringUnits
    ws.Range("B8").Value = expiredUnits

    Application.ScreenUpdating = True
End Sub

' Helper function to get column number by name
Function GetColumnNumber(sheetName As String, columnName As String) As Long
    Dim ws As Worksheet
    Set ws = Sheets(sheetName)

    Dim lastCol As Long
    lastCol = ws.Cells(1, ws.Columns.Count).End(xlToLeft).Column

    Dim i As Long
    For i = 1 To lastCol
        If LCase(Trim(ws.Cells(1, i).Value)) = LCase(columnName) Then
            GetColumnNumber = i
            Exit Function
        End If
    Next i

    GetColumnNumber = 0
End Function

' Navigate to sheet
Sub GoToReagents()
    Sheets("Reagents").Select
    Range("A1").Select
End Sub

Sub GoToUnits()
    Sheets("Reagent_Units").Select
    Range("A1").Select
End Sub

Sub GoToPanels()
    Sheets("Panels").Select
    Range("A1").Select
End Sub

Sub GoToDashboard()
    Call RefreshDashboard
    Sheets("Dashboard").Select
    Range("A1").Select
End Sub
