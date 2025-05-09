## **1\. Set Mandatory Field Checks**

Mandatory field checks ensure that critical fields are populated with valid data before submission. This prevents incomplete or invalid entries from being processed downstream.

### **Critical Fields for Validation**

- **Supplier_Name**: Must be present and non-empty.
- **Category**: Ensure a valid category (e.g., STEM, Electronics, etc.).
- **Sub-Category**: Sub-categories must be aligned with categories.
- **Supplier_SKU**: Unique identifier for the product; required for tracking.
- **Unit_Cost_Price_ex_GST**: Must be numeric and non-negative.
- **Tax_Rate**: Ensure a valid percentage (e.g., 10% as 0.1).
- **RRP_inc_GST**: Retail price must be greater than cost price.
- **Product_Name**: Descriptive and unique name required.
- **Barcode_GTIN**: Mandatory if the product is sold in retail; validate GTIN-13 format.
- **Image_Link_1**: At least one image link should be present and valid (e.g., starts with `http`).

### **Validation Options**

1.  **In Excel Using Data Validation**: Use Excel’s **Data Validation** feature to enforce rules for mandatory fields.
    
    - **Numeric Fields**:
        - Select the column → Go to `Data` → `Data Validation`.
        - Set criteria like “Decimal > 0” for prices and percentages.
    - **Non-Empty Text Fields**:
        - Set criteria to “Text Length > 0” for fields like `Supplier_Name`, `Product_Name`.
    - **Drop-down Lists**:
        - Create a list of allowed values for fields like `Category` and `Sub-Category`.
    - **URLs**:
        - Use custom formula to validate URLs, e.g., `=ISNUMBER(FIND("http", A1))`.
2.  **Automated Validation with Python**: Implement validation logic in a Python script using **pandas** to identify missing or malformed fields. For example:
    
    ```py
    import pandas as pd
    
    # Load the Excel file
    df = pd.read_excel("Product_Catalog_Submission.xlsx")
    
    # Define validation rules
    errors = []
    
    if df["Supplier_Name"].isnull().any():
        errors.append("Supplier_Name is missing for some rows.")
    if (df["Unit_Cost_Price_ex_GST"] <= 0).any():
        errors.append("Unit_Cost_Price_ex_GST must be greater than 0.")
    if df["Product_Name"].isnull().any():
        errors.append("Product_Name is missing.")
    
    # Print errors
    if errors:
        for error in errors:
            print(error)
    else:
        print("Validation passed!")
    ```
    
3.  **In Submission Forms**: If the data is submitted through an online form, use server-side and client-side validation:
    
    - Use JavaScript to ensure fields are filled before submission.
    - Add backend validation to reject invalid data.

* * *

## **2\. Use Templates**

Providing users with a well-structured Excel template ensures data is submitted in the correct format and minimizes errors.

### **Template Design**

1.  **Include Guidelines**:
    
    - Add a header row with tooltips or comments to describe each field.
    - For example, `Unit_Cost_Price_ex_GST`: “Enter numeric value (e.g., 500.00) without currency symbols.”
2.  **Set Formatting**:
    
    - Lock critical formatting like column widths, numeric formats, and date formats.
    - Use conditional formatting to highlight errors:
        - Example: Red background for negative prices.
    - Set default formatting:
        - Dates: `YYYY-MM-DD`.
        - Percentages: `0.0%`.
3.  **Pre-Filled Data for Dropdowns**:
    
    - Use drop-down lists for fields with predefined options (e.g., categories, tax rates):
        - In Excel, use the `Data Validation` → `List` option and specify allowed values.
4.  **Highlight Mandatory Fields**:
    
    - Use bold or colored headers for mandatory fields.
    - Example: Highlight columns `Supplier_Name`, `Product_Name`, and `Supplier_SKU`.

### **Example Template**

| Supplier_Name | Category | Sub-Category | Supplier_SKU | Unit_Cost_Price_ex_GST | Tax_Rate | RRP_inc_GST | Product_Name | Barcode_GTIN | Image_Link_1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Meubilair_Direct | STEM | Robotics | SKU12345 | 500.00 | 0.10 | 682.00 | Robotic Arm | 1234567890123 | http://example.com/img1 |
| \[Enter Supplier Name\] | \[Select\] | \[Select\] | \[Enter SKU\] | \[Enter Price\] | \[0.10\] | \[Calculate\] | \[Enter Name\] | \[Optional\] | \[Enter Image URL\] |

* * *

### **Instructions for Users**

1.  **Read Guidelines**:
    
    - Include a separate sheet in the template with detailed instructions for each field, including examples.
2.  **Test Before Submission**:
    
    - Ask users to run a macro or script that highlights issues in their data before submission.
3.  **Provide Example Rows**:
    
    - Add a few sample rows as references.
4.  **Submission Checklist**:
    
    - Ensure users check all mandatory fields are filled, data is correctly formatted, and files are exported in CSV format.

* * *

### **Template Distribution and Feedback**

1.  **Distribution**:
    
    - Share the template via email, SharePoint, or other collaboration tools.
    - Include a user guide (e.g., PDF or video tutorial) explaining how to fill it.
2.  **Feedback Mechanism**:
    
    - Allow users to report difficulties with the template and adjust it as necessary.

* * *

### **Advanced Features for Robust Templates**

1.  **Macro-Enabled Templates**:
    
    - Use Excel VBA to create a button that validates the data and highlights issues.
        
    - Example VBA snippet for mandatory field check:
        

```vb
Sub ValidateFields()
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim i As Long
    
    Set ws = ThisWorkbook.Sheets("Sheet1")
    lastRow = ws.Cells(ws.Rows.Count, "A").End(xlUp).Row
    
    For i = 2 To lastRow
        If ws.Cells(i, 1).Value = "" Then
            ws.Cells(i, 1).Interior.Color = vbRed ' Highlight missing Supplier_Name
        End If
    Next i
    
    MsgBox "Validation Complete!"
End Sub
```

* * *
