"""LLM-based product extraction from emails"""

import json
from typing import List
from langchain_core.messages import HumanMessage
from src.models.email import Email
from src.models.product import ProductMention, ProductProperty
from src.llm.client import get_llm_client
from src.config.config_loader import load_config


def build_extraction_prompt(email: Email) -> str:
    """
    Build the prompt for product extraction.

    Args:
        email: Email to extract products from

    Returns:
        Formatted prompt string
    """
    config = load_config()

    # Build product definitions section
    products_info = []
    for product in config.products:
        props = [prop.name for prop in product.properties]
        products_info.append(
            f"- {product.name} ({product.category}): "
            f"aliases={product.aliases}, properties={props}"
        )

    products_section = "\n".join(products_info)

    # Use cleaned body if available, otherwise raw body
    email_content = email.cleaned_body if email.cleaned_body else email.body

    prompt = f"""You are analyzing business emails about industrial products and fasteners.

PRODUCT DEFINITIONS:
{products_section}

TASK:
Extract all product mentions from the email below. For each product, identify:
1. Product name and category (from the definitions above)
2. Properties (grade, size, material, finish, etc.)
3. Quantity if mentioned
4. Context (quote_request, order, inquiry, pricing_request, etc.)
5. Any dates mentioned related to the product request

EMAIL SUBJECT: {email.metadata.subject}
EMAIL BODY:
{email_content}

Return a JSON object with this structure:
{{
    "products": [
        {{
            "product_name": "string",
            "product_category": "string",
            "properties": {{"property_name": "value"}},
            "quantity": number or null,
            "unit": "string or null",
            "context": "string"
        }}
    ]
}}

If no products are found, return {{"products": []}}.
Only return valid JSON, no additional text.
"""

    return prompt


def extract_products_from_email(email: Email) -> List[ProductMention]:
    """
    Extract product mentions from an email using LLM.

    Args:
        email: Email to process

    Returns:
        List of ProductMention objects
    """
    try:
        # Get LLM client
        llm = get_llm_client()

        # Build prompt
        prompt = build_extraction_prompt(email)

        # Call LLM (synchronous invoke)
        response = llm.invoke([HumanMessage(content=prompt)])

        # Parse JSON response
        try:
            content = response.content
            if isinstance(content, str):
                result = json.loads(content)
            else:
                # If content is not a string, try to convert it
                result = json.loads(str(content))
        except json.JSONDecodeError:
            print(
                f"Warning: Failed to parse LLM response as JSON for {email.file_path}"
            )
            return []

        # Convert to ProductMention objects
        products = []
        for product_data in result.get("products", []):
            try:
                # Convert properties dict to List[ProductProperty]
                properties = []
                for prop_name, prop_value in product_data.get("properties", {}).items():
                    properties.append(
                        ProductProperty(
                            name=prop_name, value=str(prop_value), confidence=1.0
                        )
                    )

                # Create ProductMention with email metadata
                mention = ProductMention(
                    product_name=product_data["product_name"],
                    product_category=product_data["product_category"],
                    properties=properties,
                    quantity=product_data.get("quantity"),
                    unit=product_data.get("unit"),
                    context=product_data.get("context", "unknown"),
                    date_requested=None,  # TODO: Parse dates from email
                    email_subject=email.metadata.subject,
                    email_sender=email.metadata.sender,
                    email_date=email.metadata.date,
                    email_file=email.file_path,
                )

                products.append(mention)
            except Exception as e:
                print(
                    f"Warning: Failed to create ProductMention from {product_data}: {e}"
                )
                continue

        return products

    except Exception as e:
        print(f"Error extracting products from email {email.file_path}: {e}")
        return []


def extract_products_batch(emails: List[Email]) -> List[ProductMention]:
    """
    Extract products from multiple emails.

    Args:
        emails: List of emails to process

    Returns:
        List of all ProductMention objects from all emails
    """
    all_products = []

    for email in emails:
        products = extract_products_from_email(email)
        all_products.extend(products)

    return all_products
