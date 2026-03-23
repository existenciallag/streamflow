Attribute VB_Name = "Panels"
' =============================================================================
' StreamFlow - Panel Management Module
' =============================================================================
' Functions for managing antibody panels
' =============================================================================

Option Explicit

' View panel details
Sub ViewPanelDetails()
    Dim panelName As String

    panelName = Application.InputBox("Enter Panel Name or ID:", "View Panel", Type:=2)
    If panelName = "False" Or panelName = "" Then Exit Sub

    ' Find panel
    Dim wsPanels As Worksheet
    Dim wsPanelReagents As Worksheet
    Set wsPanels = Sheets("Panels")
    Set wsPanelReagents = Sheets("Panel_Reagents")

    Dim lastRow As Long
    lastRow = wsPanels.Cells(wsPanels.Rows.Count, 1).End(xlUp).Row

    Dim i As Long
    Dim foundRow As Long
    Dim panelID As String
    foundRow = 0

    For i = 2 To lastRow
        If LCase(Trim(wsPanels.Cells(i, GetColumnNumber("Panels", "name")).Value)) = LCase(Trim(panelName)) Or _
           wsPanels.Cells(i, 1).Value = panelName Then
            foundRow = i
            panelID = wsPanels.Cells(i, 1).Value
            Exit For
        End If
    Next i

    If foundRow = 0 Then
        MsgBox "Panel not found: " & panelName, vbExclamation
        Exit Sub
    End If

    ' Build panel info
    Dim info As String
    info = "Panel: " & wsPanels.Cells(foundRow, GetColumnNumber("Panels", "name")).Value & vbCrLf
    info = info & "ID: " & panelID & vbCrLf
    info = info & "Description: " & wsPanels.Cells(foundRow, GetColumnNumber("Panels", "description")).Value & vbCrLf
    info = info & vbCrLf & "Reagents in panel:" & vbCrLf

    ' Find reagents in this panel
    Dim lastPRRow As Long
    lastPRRow = wsPanelReagents.Cells(wsPanelReagents.Rows.Count, 1).End(xlUp).Row

    Dim reagentCount As Long
    reagentCount = 0

    For i = 2 To lastPRRow
        If wsPanelReagents.Cells(i, GetColumnNumber("Panel_Reagents", "panel_id")).Value = panelID Then
            Dim reagentID As String
            reagentID = wsPanelReagents.Cells(i, GetColumnNumber("Panel_Reagents", "reagent_id")).Value

            ' Get reagent name
            Dim reagentName As String
            reagentName = GetReagentName(reagentID)

            reagentCount = reagentCount + 1
            info = info & "  " & reagentCount & ". " & reagentName & vbCrLf
        End If
    Next i

    If reagentCount = 0 Then
        info = info & "  (No reagents assigned)" & vbCrLf
    End If

    MsgBox info, vbInformation, "Panel Details"
End Sub

' List all panels
Sub ListAllPanels()
    Dim ws As Worksheet
    Set ws = Sheets("Panels")

    Dim lastRow As Long
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    If lastRow < 2 Then
        MsgBox "No panels found.", vbInformation
        Exit Sub
    End If

    Dim info As String
    info = "Available Panels:" & vbCrLf & vbCrLf

    Dim i As Long
    For i = 2 To lastRow
        info = info & ws.Cells(i, GetColumnNumber("Panels", "name")).Value & vbCrLf
    Next i

    MsgBox info, vbInformation, "All Panels"
End Sub

' Helper: Get reagent name by ID
Function GetReagentName(reagentID As String) As String
    Dim ws As Worksheet
    Set ws = Sheets("Reagents")

    Dim lastRow As Long
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    Dim i As Long
    For i = 2 To lastRow
        If ws.Cells(i, 1).Value = reagentID Then
            GetReagentName = ws.Cells(i, GetColumnNumber("Reagents", "name")).Value
            Exit Function
        End If
    Next i

    GetReagentName = "(Unknown)"
End Function

' Check stock availability for panel
Sub CheckPanelStock()
    Dim panelName As String

    panelName = Application.InputBox("Enter Panel Name or ID:", "Check Stock", Type:=2)
    If panelName = "False" Or panelName = "" Then Exit Sub

    ' Find panel
    Dim wsPanels As Worksheet
    Dim wsPanelReagents As Worksheet
    Dim wsUnits As Worksheet
    Set wsPanels = Sheets("Panels")
    Set wsPanelReagents = Sheets("Panel_Reagents")
    Set wsUnits = Sheets("Reagent_Units")

    Dim lastRow As Long
    lastRow = wsPanels.Cells(wsPanels.Rows.Count, 1).End(xlUp).Row

    Dim i As Long
    Dim foundRow As Long
    Dim panelID As String
    foundRow = 0

    For i = 2 To lastRow
        If LCase(Trim(wsPanels.Cells(i, GetColumnNumber("Panels", "name")).Value)) = LCase(Trim(panelName)) Or _
           wsPanels.Cells(i, 1).Value = panelName Then
            foundRow = i
            panelID = wsPanels.Cells(i, 1).Value
            Exit For
        End If
    Next i

    If foundRow = 0 Then
        MsgBox "Panel not found: " & panelName, vbExclamation
        Exit Sub
    End If

    ' Build stock info
    Dim info As String
    info = "Stock Availability - " & wsPanels.Cells(foundRow, GetColumnNumber("Panels", "name")).Value & vbCrLf & vbCrLf

    ' Find reagents in this panel
    Dim lastPRRow As Long
    lastPRRow = wsPanelReagents.Cells(wsPanelReagents.Rows.Count, 1).End(xlUp).Row

    Dim reagentCount As Long
    reagentCount = 0
    Dim allAvailable As Boolean
    allAvailable = True

    For i = 2 To lastPRRow
        If wsPanelReagents.Cells(i, GetColumnNumber("Panel_Reagents", "panel_id")).Value = panelID Then
            Dim reagentID As String
            reagentID = wsPanelReagents.Cells(i, GetColumnNumber("Panel_Reagents", "reagent_id")).Value

            ' Get reagent name
            Dim reagentName As String
            reagentName = GetReagentName(reagentID)

            ' Count available units
            Dim availableUnits As Long
            availableUnits = CountAvailableUnits(reagentID)

            reagentCount = reagentCount + 1
            info = info & reagentName & ": "

            If availableUnits > 0 Then
                info = info & "✓ " & availableUnits & " units available" & vbCrLf
            Else
                info = info & "✗ OUT OF STOCK" & vbCrLf
                allAvailable = False
            End If
        End If
    Next i

    If reagentCount = 0 Then
        info = info & "(No reagents in panel)" & vbCrLf
    Else
        info = info & vbCrLf
        If allAvailable Then
            info = info & "✓ All reagents available"
        Else
            info = info & "⚠ Some reagents out of stock"
        End If
    End If

    MsgBox info, vbInformation, "Panel Stock Check"
End Sub

' Helper: Count available units for a reagent
Function CountAvailableUnits(reagentID As String) As Long
    Dim ws As Worksheet
    Set ws = Sheets("Reagent_Units")

    Dim lastRow As Long
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    Dim count As Long
    count = 0

    Dim i As Long
    For i = 2 To lastRow
        If ws.Cells(i, GetColumnNumber("Reagent_Units", "reagent_id")).Value = reagentID Then
            Dim status As String
            status = UCase(Trim(ws.Cells(i, GetColumnNumber("Reagent_Units", "status")).Value))

            If status = "STORED" Or status = "IN USE" Then
                count = count + 1
            End If
        End If
    Next i

    CountAvailableUnits = count
End Function
