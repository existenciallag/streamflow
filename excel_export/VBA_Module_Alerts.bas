Attribute VB_Name = "Alerts"
' =============================================================================
' StreamFlow - Alerts and Reporting Module
' =============================================================================
' Functions for expiration alerts, low stock warnings, and reports
' =============================================================================

Option Explicit

' Check expiring units
Sub CheckExpiringUnits()
    Dim ws As Worksheet
    Set ws = Sheets("Reagent_Units")

    Dim lastRow As Long
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    Dim today As Date
    today = Date

    Dim info As String
    info = "EXPIRATION ALERTS" & vbCrLf & vbCrLf

    Dim expiredCount As Long
    Dim expiringCount As Long
    expiredCount = 0
    expiringCount = 0

    ' Expired units
    info = info & "=== EXPIRED ===" & vbCrLf

    Dim i As Long
    Dim expirationDate As Date
    Dim reagentID As String
    Dim lot As String

    For i = 2 To lastRow
        On Error Resume Next
        expirationDate = ws.Cells(i, GetColumnNumber("Reagent_Units", "expiration_date")).Value
        If Err.Number = 0 And expirationDate > 0 Then
            If expirationDate < today Then
                reagentID = ws.Cells(i, GetColumnNumber("Reagent_Units", "reagent_id")).Value
                lot = ws.Cells(i, GetColumnNumber("Reagent_Units", "lot")).Value

                info = info & GetReagentName(reagentID) & " (Lot: " & lot & ") - " & _
                       Format(expirationDate, "yyyy-mm-dd") & vbCrLf

                expiredCount = expiredCount + 1
            End If
        End If
        On Error GoTo 0
    Next i

    If expiredCount = 0 Then
        info = info & "(None)" & vbCrLf
    End If

    ' Expiring soon (next 30 days)
    info = info & vbCrLf & "=== EXPIRING SOON (30 days) ===" & vbCrLf

    For i = 2 To lastRow
        On Error Resume Next
        expirationDate = ws.Cells(i, GetColumnNumber("Reagent_Units", "expiration_date")).Value
        If Err.Number = 0 And expirationDate > 0 Then
            If expirationDate >= today And expirationDate <= today + 30 Then
                reagentID = ws.Cells(i, GetColumnNumber("Reagent_Units", "reagent_id")).Value
                lot = ws.Cells(i, GetColumnNumber("Reagent_Units", "lot")).Value

                info = info & GetReagentName(reagentID) & " (Lot: " & lot & ") - " & _
                       Format(expirationDate, "yyyy-mm-dd") & " (" & _
                       (expirationDate - today) & " days)" & vbCrLf

                expiringCount = expiringCount + 1
            End If
        End If
        On Error GoTo 0
    Next i

    If expiringCount = 0 Then
        info = info & "(None)" & vbCrLf
    End If

    info = info & vbCrLf & "Total: " & expiredCount & " expired, " & expiringCount & " expiring soon"

    MsgBox info, vbExclamation, "Expiration Alerts"
End Sub

' Check low stock
Sub CheckLowStock()
    Dim wsReagents As Worksheet
    Dim wsUnits As Worksheet
    Set wsReagents = Sheets("Reagents")
    Set wsUnits = Sheets("Reagent_Units")

    Dim lastRow As Long
    lastRow = wsReagents.Cells(wsReagents.Rows.Count, 1).End(xlUp).Row

    Dim info As String
    info = "LOW STOCK ALERT" & vbCrLf & vbCrLf

    Dim lowStockCount As Long
    lowStockCount = 0

    Dim i As Long
    Dim reagentID As String
    Dim reagentName As String
    Dim availableUnits As Long

    For i = 2 To lastRow
        reagentID = wsReagents.Cells(i, 1).Value
        reagentName = wsReagents.Cells(i, GetColumnNumber("Reagents", "name")).Value

        availableUnits = CountAvailableUnits(reagentID)

        If availableUnits <= 2 Then
            info = info & reagentName & ": " & availableUnits & " units"

            If availableUnits = 0 Then
                info = info & " ⚠ OUT OF STOCK"
            ElseIf availableUnits = 1 Then
                info = info & " ⚠ CRITICAL"
            Else
                info = info & " ⚠ LOW"
            End If

            info = info & vbCrLf
            lowStockCount = lowStockCount + 1
        End If
    Next i

    If lowStockCount = 0 Then
        info = info & "✓ All reagents have sufficient stock (>2 units)" & vbCrLf
    Else
        info = info & vbCrLf & "Total: " & lowStockCount & " reagents need attention"
    End If

    MsgBox info, vbExclamation, "Low Stock Alert"
End Sub

' Generate inventory report
Sub GenerateInventoryReport()
    Dim ws As Worksheet
    Set ws = Sheets("Reagent_Units")

    Dim lastRow As Long
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    ' Create new sheet for report
    Dim wsReport As Worksheet
    On Error Resume Next
    Application.DisplayAlerts = False
    Worksheets("Inventory_Report").Delete
    Application.DisplayAlerts = True
    On Error GoTo 0

    Set wsReport = Worksheets.Add(After:=Worksheets(Worksheets.Count))
    wsReport.Name = "Inventory_Report"

    ' Headers
    wsReport.Cells(1, 1).Value = "Reagent"
    wsReport.Cells(1, 2).Value = "Clone"
    wsReport.Cells(1, 3).Value = "Fluorochrome"
    wsReport.Cells(1, 4).Value = "Total Units"
    wsReport.Cells(1, 5).Value = "In Use"
    wsReport.Cells(1, 6).Value = "Stored"
    wsReport.Cells(1, 7).Value = "Empty"
    wsReport.Cells(1, 8).Value = "Status"

    ' Format header
    With wsReport.Range("A1:H1")
        .Font.Bold = True
        .Interior.Color = RGB(79, 129, 189)
        .Font.Color = RGB(255, 255, 255)
    End With

    ' Get unique reagents
    Dim wsReagents As Worksheet
    Set wsReagents = Sheets("Reagents")

    Dim lastReagentRow As Long
    lastReagentRow = wsReagents.Cells(wsReagents.Rows.Count, 1).End(xlUp).Row

    Dim reportRow As Long
    reportRow = 2

    Dim i As Long
    For i = 2 To lastReagentRow
        Dim reagentID As String
        Dim reagentName As String
        Dim clone As String
        Dim fluoro As String

        reagentID = wsReagents.Cells(i, 1).Value
        reagentName = wsReagents.Cells(i, GetColumnNumber("Reagents", "name")).Value
        clone = wsReagents.Cells(i, GetColumnNumber("Reagents", "clone")).Value
        fluoro = GetFluorochromeName(wsReagents.Cells(i, GetColumnNumber("Reagents", "fluorochrome")).Value)

        ' Count units by status
        Dim totalUnits As Long
        Dim inUse As Long
        Dim stored As Long
        Dim empty As Long

        Call CountUnitsByStatus(reagentID, totalUnits, inUse, stored, empty)

        ' Status
        Dim statusText As String
        If totalUnits = 0 Then
            statusText = "NO UNITS"
        ElseIf stored + inUse = 0 Then
            statusText = "OUT OF STOCK"
        ElseIf stored + inUse <= 2 Then
            statusText = "LOW STOCK"
        Else
            statusText = "OK"
        End If

        ' Write to report
        wsReport.Cells(reportRow, 1).Value = reagentName
        wsReport.Cells(reportRow, 2).Value = clone
        wsReport.Cells(reportRow, 3).Value = fluoro
        wsReport.Cells(reportRow, 4).Value = totalUnits
        wsReport.Cells(reportRow, 5).Value = inUse
        wsReport.Cells(reportRow, 6).Value = stored
        wsReport.Cells(reportRow, 7).Value = empty
        wsReport.Cells(reportRow, 8).Value = statusText

        ' Color code status
        Select Case statusText
            Case "NO UNITS", "OUT OF STOCK"
                wsReport.Cells(reportRow, 8).Interior.Color = RGB(255, 0, 0)
            Case "LOW STOCK"
                wsReport.Cells(reportRow, 8).Interior.Color = RGB(255, 192, 0)
            Case "OK"
                wsReport.Cells(reportRow, 8).Interior.Color = RGB(146, 208, 80)
        End Select

        reportRow = reportRow + 1
    Next i

    ' Auto-fit columns
    wsReport.Columns("A:H").AutoFit

    ' Select report sheet
    wsReport.Select
    Range("A1").Select

    MsgBox "Inventory report generated successfully!", vbInformation
End Sub

' Helper: Count units by status
Sub CountUnitsByStatus(reagentID As String, ByRef total As Long, ByRef inUse As Long, ByRef stored As Long, ByRef empty As Long)
    Dim ws As Worksheet
    Set ws = Sheets("Reagent_Units")

    Dim lastRow As Long
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    total = 0
    inUse = 0
    stored = 0
    empty = 0

    Dim i As Long
    For i = 2 To lastRow
        If ws.Cells(i, GetColumnNumber("Reagent_Units", "reagent_id")).Value = reagentID Then
            total = total + 1

            Dim status As String
            status = UCase(Trim(ws.Cells(i, GetColumnNumber("Reagent_Units", "status")).Value))

            Select Case status
                Case "IN USE"
                    inUse = inUse + 1
                Case "STORED"
                    stored = stored + 1
                Case "EMPTY"
                    empty = empty + 1
            End Select
        End If
    Next i
End Sub

' Helper: Get fluorochrome name by ID
Function GetFluorochromeName(fluoroID As String) As String
    Dim ws As Worksheet
    Set ws = Sheets("Fluorochromes")

    Dim lastRow As Long
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    Dim i As Long
    For i = 2 To lastRow
        If ws.Cells(i, 1).Value = fluoroID Then
            GetFluorochromeName = ws.Cells(i, GetColumnNumber("Fluorochromes", "name")).Value
            Exit Function
        End If
    Next i

    GetFluorochromeName = ""
End Function
