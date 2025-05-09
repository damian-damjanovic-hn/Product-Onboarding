# Product Catalog Workflow

Automated workflow for enhancing product descriptions and submitting product details to Magento 2 using Microsoft Forms, OpenAI, and Power Automate.

## Overview

This project implements a streamlined workflow for:

- Collecting product data via Microsoft Forms.
- Enhancing product descriptions using OpenAI for better SEO and clarity.
- Submitting the enhanced data to Magento 2 via its REST API.

The goal is to automate the product catalog submission process, reducing manual effort and ensuring high-quality product descriptions.

* * *

## Features

- **Data Collection:** Vendor submissions using Microsoft Forms.
- **AI-Powered Description Enhancement:** Integrates with OpenAI to refine product descriptions.
- **Seamless Integration with Magento 2:** Utilizes Magento’s REST API for product creation and updates.
- **Error Handling:** Includes robust mechanisms for managing API failures.
- **Notifications:** Alerts and logs for successful and failed operations.

* * *

## Workflow Steps

1.  **Trigger:**
    - Start the workflow when a vendor submits the Microsoft Form.
2.  **Enhance Description:**
    - Send the product description to OpenAI for improvement.
3.  **Prepare Product Data:**
    - Combine the enhanced description with other form data into Magento-compatible JSON.
4.  **Submit to Magento 2:**
    - Send the data to Magento via its REST API.
5.  **Handle Response:**
    - Log success or failure and notify relevant stakeholders.

* * *

## Directory Structure

```txt
product-catalog-workflow/
├── README.md                # Project overview and documentation
├── .gitignore               # Excludes sensitive or unnecessary files
├── docs/                    # Workflow documentation and diagrams
├── scripts/                 # Power Automate JSON templates
├── tests/                   # Testing scripts and validation tools
├── config/                  # Configurations for API keys and other settings
```

* * *

## Getting Started

### Prerequisites

1.  **Git**: Install Git to clone and manage this repository.
2.  **Power Automate Account**: Required for setting up the workflow.
3.  **Magento 2 API Access**:
    - API endpoint: `https://your-magento-domain/rest/V1/products`
    - Authentication token.
4.  **OpenAI API Key**:
    - Sign up at [OpenAI](https://openai.com/) to obtain an API key.

* * *

### Setup Instructions

1.  Clone the repository:
    
    ```bash
    git clone https://github.com/<your-username>/product-catalog-workflow.git
    cd product-catalog-workflow
    ```
    
2.  Set up configuration files:
    
    - Create a file in `config/` named `api_keys.json`:
        
        ```json
        {
          "openai_api_key": "<Your-OpenAI-API-Key>",
          "magento_api_token": "<Your-Magento-Token>"
        }
        ```
        
3.  Import the Power Automate templates:
    
    - Go to **Power Automate** and import JSON files from the `scripts/` directory.
4.  Customize the Power Automate flows:
    
    - Replace placeholder values with your specific API keys, URLs, and form IDs.

* * *

## API Integrations

### OpenAI

- **Endpoint:** `https://api.openai.com/v1/completions`
- **Method:** POST
- **Headers:**
    - `Authorization: Bearer <Your-OpenAI-API-Key>`
    - `Content-Type: application/json`

### Magento 2

- **Endpoint:** `https://your-magento-domain/rest/V1/products`
- **Method:** POST
- **Headers:**
    - `Authorization: Bearer <Your-Magento-Token>`
    - `Content-Type: application/json`

* * *

## Contributing

Contributions are welcome! To contribute:

1.  Fork the repository.
    
2.  Create a feature branch:
    
    ```bash
    git checkout -b feature-name
    ```
    
3.  Commit your changes:
    
    ```bash
    git commit -m "Add detailed description enhancement step"
    ```
    
4.  Push to your branch:
    
    ```bash
    git push origin feature-name
    ```
    
5.  Submit a pull request.
    

* * *

## License

Copyright Damian Damjanovic 2024

* * *

## Acknowledgments

- [Microsoft Power Automate](https://powerautomate.microsoft.com/)
- [OpenAI](https://openai.com/)
- [Magento 2](https://magento.com/)
