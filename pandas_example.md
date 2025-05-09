
## Python script using Pandas to process Excel data:
**Whether it’s data cleaning, aggregation, visualization, or handling large datasets, pandas offers efficient and powerful tools to streamline workflows.**

1.  **Loading data from an Excel file**
    
2.  **Cleaning data**
    
3.  **Handling tax calculations**
    
4.  **Aggregating and grouping data**
    
5.  **Exporting data to a CSV file**
    

### Step 1: Install Required Libraries

```sh
pip install pandas openpyxl
```

### Step 2: The `app.py` script


```python
import pandas as pd

def load_excel(file_path, sheet_name):
    """Load data from an Excel file."""
    return pd.read_excel(file_path, sheet_name=sheet_name)

def clean_data(df):
    """Clean data by replacing line breaks and converting to strings."""
    return df.applymap(lambda x: str(x).replace('\n', ' ').replace('\r', ' ') if isinstance(x, str) else x)

def add_tax(df, tax_rate=0.10):
    """Add a new column for unit cost price including tax."""
    df['Unit_Cost_Price_inc_GST'] = df['Unit_Cost_Price_ex_GST'] * (1 + tax_rate)
    return df

def adjust_markup(df, markup_percentage):
    """Add a new column for price after markup."""
    df['Price_after_Markup'] = df['Unit_Cost_Price_inc_GST'] * (1 + markup_percentage)
    return df

def aggregate_data(df):
    """Aggregate data by category."""
    return df.groupby('Category').agg({'Unit_Cost_Price_ex_GST': ['mean', 'sum'], 'Stock_Qty': 'mean'})

def save_to_csv(df, file_path):
    """Save the DataFrame to a CSV file."""
    df.to_csv(file_path, index=False)

def main():
    # File paths and sheet names
    input_file_path = 'your_file.xlsx'
    submission_sheet = 'Submission'
    completed_sheet = 'Completed'
    output_file_path = 'CompletedProducts.csv'

    # Load data from the Submission sheet
    df_submission = load_excel(input_file_path, submission_sheet)
    
    # Clean the data
    df_clean = clean_data(df_submission)
    
    # Add tax to unit cost price
    df_with_tax = add_tax(df_clean)
    
    # Adjust markup
    markup_percentage = 0.20  # Adjust this value as needed
    df_final = adjust_markup(df_with_tax, markup_percentage)
    
    # Save the cleaned and processed data to the Completed sheet in Excel
    with pd.ExcelWriter(input_file_path, mode='a', engine='openpyxl', if_sheet_exists='replace') as writer:
        df_final.to_excel(writer, sheet_name=completed_sheet, index=False)
    
    # Save the cleaned and processed data to a CSV file
    save_to_csv(df_final, output_file_path)
    
    print(f"Data has been processed and saved to '{completed_sheet}' sheet and '{output_file_path}'")

if __name__ == "__main__":
    main()
```

### Explanation of `app.py` Script

1.  **Load Excel Data**: The script loads data from the specified Excel file and sheet.
    
2.  **Clean Data**: It cleans the data by replacing line breaks and converting cell contents to strings.
    
3.  **Tax Calculation**: It adds a new column to calculate unit cost price including GST.
    
4.  **Markup Adjustment**: It calculates the price after applying a markup percentage.
    
5.  **Aggregate Data**: It aggregates data by category (though this function can be called as needed).
    
6.  **Save Data**: It saves the processed data back to the Excel file in the “Completed” sheet and exports it to a CSV file.
    

### Running the Script

1.  Save the script as `app.py`.
    
2.  Ensure your Excel file is in the same directory or provide the correct path.
    
3.  Run the script:
    
    ```sh
    python app.py
    ```

This script will process your data, clean it, add tax, adjust markup, and save the results to both the Excel file and a CSV file in your local directory.
