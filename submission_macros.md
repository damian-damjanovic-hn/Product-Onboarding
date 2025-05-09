## VBA Macro to Process Data

In “Submission” worksheet, fix the line break issues, convert the cell content to strings, and then copy the processed data to the “Completed” worksheet.

### Explanation

- **Set Start Column**: The macro sets the start column to M.
    
- **Set End Column**: It sets the end column to the last used column in the row.
    
- **Loop Through Specified Range**: It loops through each cell in the specified columns and rows, checking for line breaks and replacing them with spaces.
    
- **Convert to String**: Converts the cell content to a string.
    
- **Copy Data**: After processing, it finds the last row in the “Submission” sheet and the next empty row in the “Completed” sheet, then copies the data as values to the “Completed” sheet.
    

#### VBA Code

```vb
Sub FixAndCopyData()
    Dim wsSubmission As Worksheet
    Dim wsCompleted As Worksheet
    Dim cell As Range
    Dim cellContent As String
    Dim lastRow As Long
    Dim nextRow As Long
    Dim col As Integer
    Dim startCol As Integer
    Dim endCol As Integer
    
    ' Set the worksheets
    Set wsSubmission = ThisWorkbook.Sheets("Submission")
    Set wsCompleted = ThisWorkbook.Sheets("Completed")
    
    ' Set the start column for processing (Column M)
    startCol = wsSubmission.Range("M1").Column
    ' Set the end column as the last used column in the row
    endCol = wsSubmission.Cells(1, wsSubmission.Columns.Count).End(xlToLeft).Column
    
    ' Loop through the specified columns and rows
    For col = startCol To endCol
        For Each cell In wsSubmission.Range(wsSubmission.Cells(2, col), wsSubmission.Cells(wsSubmission.Rows.Count, col).End(xlUp))
            ' Check if the cell contains a line break and is not empty
            If Not IsEmpty(cell.Value) Then
                If InStr(cell.Value, vbLf) > 0 Or InStr(cell.Value, vbCr) > 0 Then
                    ' Replace line breaks with spaces
                    cellContent = Replace(cell.Value, vbLf, " ")
                    cellContent = Replace(cellContent, vbCr, " ")
                    ' Convert the cell content to a string
                    cell.Value = CStr(cellContent)
                End If
            End If
        Next cell
    Next col

    ' Find the last row in the Submission sheet
    lastRow = wsSubmission.Cells(wsSubmission.Rows.Count, "A").End(xlUp).Row

    ' Find the next empty row in the Completed sheet
    nextRow = wsCompleted.Cells(wsCompleted.Rows.Count, "A").End(xlUp).Row + 1
    
    ' Copy processed data to the Completed sheet
    wsSubmission.Range("A1:Z" & lastRow).Copy
    wsCompleted.Range("A" & nextRow).PasteSpecial Paste:=xlPasteValues

    ' Clear the clipboard
    Application.CutCopyMode = False
End Sub
```



## Loop through each record in the “Completed” sheet and output a CSV file in local downloads folder.

### Explanation

- **Worksheet and Path Setup**: The macro sets the “Completed” worksheet and defines the path for the CSV file in the local Downloads folder.
    
- **File Handling**: It opens the CSV file for writing and loops through each row, concatenating cell values and writing them to the file.
    
- **CSV Creation**: It writes each line to the CSV file, removes the trailing comma, and closes the file.
    
- **User Notification**: The macro displays a message box with the file path of the saved CSV.

#### VBA Code

```vb
Sub ExportToCSV()
    Dim wsCompleted As Worksheet
    Dim lastRow As Long
    Dim csvFilePath As String
    Dim cell As Range
    Dim line As String
    Dim fileNum As Integer
    Dim downloadPath As String

    ' Set the worksheet
    Set wsCompleted = ThisWorkbook.Sheets("Completed")
    
    ' Find the last row in the Completed sheet
    lastRow = wsCompleted.Cells(wsCompleted.Rows.Count, "A").End(xlUp).Row
    
    ' Define the download path (local Downloads folder)
    downloadPath = Environ("USERPROFILE") & "\Downloads\"
    csvFilePath = downloadPath & "CompletedProducts.csv"
    
    ' Open the file for writing
    fileNum = FreeFile
    Open csvFilePath For Output As fileNum
    
    ' Loop through each row and write to the CSV file
    For Each cell In wsCompleted.Range("A1:A" & lastRow).Cells
        line = ""
        For Each colCell In wsCompleted.Range(cell.Address).EntireRow.Cells
            line = line & colCell.Value & ","
        Next colCell
        ' Remove the trailing comma and write the line to the file
        Print #fileNum, Left(line, Len(line) - 1)
    Next cell
    
    ' Close the file
    Close fileNum
    
    ' Notify user of the file path
    MsgBox "CSV file has been saved to: " & csvFilePath, vbInformation
End Sub
```


### Running the Macro

1.  **Save the module** and close the VBA editor.
    
2.  **Press** `ALT + F8` to open the Macro dialog box.
    
3.  **Select** `ExportToCSV` and click `Run`.
    

This macro will loop through each record in “Completed” sheet and save the output as a CSV file in local Downloads folder.
