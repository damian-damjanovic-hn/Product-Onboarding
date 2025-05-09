### **Updated Power Automate Flow**

#### 1\. **Trigger: When a File is Created in OneDrive**

- **Connector**: OneDrive for Business.
- **Action**: *When a file is created*.
- **Folder**: Specify the folder where the Excel files are saved in OneDrive.

* * *

#### 2\. **Get File Content**

- **Connector**: OneDrive for Business.
- **Action**: *Get file content*.
- **File Identifier**: Use dynamic content `Identifier` from the previous step.

* * *

#### 3\. **Extract Data from Excel**

- **Connector**: Excel Online (Business).
- **Action**: *List rows present in a table*.
- **Location**: OneDrive for Business.
- **Document Library**: Leave this blank (OneDrive doesn’t have libraries).
- **File**: Use dynamic content `Identifier`.
- **Table**: Specify the table name or leave it dynamic if the table is defined in the file.

* * *

#### 4\. **For Each Row: Process Data**

- **Connector**: Control.
- **Action**: *Apply to each*.
- **Input**: Use the output from *List rows present in a table*.

Inside the loop:

##### **Compose OpenAI Request**

- **Connector**: Data Operations.
    
- **Action**: *Compose*.
    
- **Name**: Prepare OpenAI Request.
    
- **Input**:
    
    j
    
    ```json
    {
      "model": "text-davinci-003",
      "prompt": "Improve the following product description for better SEO and clarity:\n\n@{items('Apply_to_each')?['Product Description']}",
      "max_tokens": 100,
      "temperature": 0.7
    }
    ```
    

##### **Send HTTP Request to OpenAI**

- **Connector**: HTTP.
    
- **Action**: *HTTP*.
    
- **Method**: POST.
    
- **URI**: `https://api.openai.com/v1/completions`.
    
- **Headers**:
    
    ```json
    {
      "Content-Type": "application/json",
      "Authorization": "Bearer <Your_OpenAI_API_Key>"
    }
    ```
    
- **Body**: Use the output from the Compose OpenAI Request step.
    

##### **Parse OpenAI Response**

- **Connector**: Data Operations.
    
- **Action**: *Parse JSON*.
    
- **Content**: `@body('Send_HTTP_Request_to_OpenAI')`.
    
- **Schema**:
    
    ```json
    {
      "type": "object",
      "properties": {
        "choices": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "text": {
                "type": "string"
              }
            }
          }
        }
      }
    }
    ```
    

##### **Extract Enhanced Description**

- **Connector**: Data Operations.
- **Action**: *Compose*.
- **Name**: Extract Enhanced Description.
- **Input**: `@outputs('Parse_OpenAI_Response')?['choices'][0]['text']`.

##### **Prepare Magento JSON**

- **Connector**: Data Operations.
    
- **Action**: *Compose*.
    
- **Name**: Prepare Magento JSON.
    
- **Input**:
    
    ```json
    {
      "product": {
        "sku": "@{items('Apply_to_each')?['SKU']}",
        "name": "@{items('Apply_to_each')?['Product Name']}",
        "price": @{items('Apply_to_each')?['RRP (inc. GST)']},
        "status": 1,
        "type_id": "simple",
        "visibility": 4,
        "attribute_set_id": 4,
        "extension_attributes": {
          "stock_item": {
            "qty": @{items('Apply_to_each')?['Stock Qty']},
            "is_in_stock": true
          }
        },
        "custom_attributes": [
          {
            "attribute_code": "supplier_code",
            "value": "@{items('Apply_to_each')?['Supplier Code']}"
          },
          {
            "attribute_code": "unit_cost_price_inc_gst",
            "value": @{items('Apply_to_each')?['Unit Cost Price (inc. GST)']}
          },
          {
            "attribute_code": "freight_cost_flat_rate_inc_gst",
            "value": @{items('Apply_to_each')?['Freight Cost Flat-Rate (inc. GST)']}
          },
          {
            "attribute_code": "description",
            "value": "@{outputs('Extract_Enhanced_Description')}"
          },
          {
            "attribute_code": "image_link_1",
            "value": "@{items('Apply_to_each')?['Image Link 1']}"
          },
          {
            "attribute_code": "image_link_2",
            "value": "@{items('Apply_to_each')?['Image link 2']}"
          },
          {
            "attribute_code": "image_link_3",
            "value": "@{items('Apply_to_each')?['Image link 3']}"
          },
          {
            "attribute_code": "brand",
            "value": "@{items('Apply_to_each')?['Brand']}"
          },
          {
            "attribute_code": "category",
            "value": "@{items('Apply_to_each')?['Category']}"
          },
          {
            "attribute_code": "start_date",
            "value": "@{items('Apply_to_each')?['Start date']}"
          },
          {
            "attribute_code": "end_date",
            "value": "@{items('Apply_to_each')?['End date']}"
          }
        ]
      }
    }
    ```
    

* * *

#### 5\. **Send Data to Magento 2**

- **Connector**: HTTP.
    
- **Action**: *HTTP*.
    
- **Method**: POST.
    
- **URI**: `https://your-magento2-domain/rest/V1/products`.
    
- **Headers**:
    
    ```json
    {
      "Content-Type": "application/json",
      "Authorization": "Bearer <Your_Magento_Token>"
    }
    ```
    
- **Body**: Use the output from the Prepare Magento JSON step.
    

* * *

#### 6\. **Handle Response**

- **Condition**: Check the status code of the Magento 2 response.
- If status code = 200:
    - Send a success email or Teams notification.
- If status code ≠ 200:
    - Log the error and notify the admin of the failure.

* * *

This updated flow triggers when a new Excel file is created in OneDrive, extracts its contents, processes the data, and sends it to Magento 2. Ensure to adjust field mappings and dynamic content to match the structure of the Excel sheet.
