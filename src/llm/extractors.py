"""LLM-based product extraction from emails"""

import json
from typing import List
from langchain_core.messages import HumanMessage
from tqdm import tqdm
from src.models.email import Email
from src.models.product import ProductMention, ProductProperty
from src.llm.client import get_llm_client
from src.config.config_loader import load_config
from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class ProductExtractionItem(BaseModel):
    """Single product extraction from email"""

    product_name: str = Field(description="Name of the product")
    product_category: str = Field(description="Category of the product")
    properties: list[ProductProperty] = Field(
        default_factory=list, description="Product properties as key-value pairs"
    )
    quantity: Optional[float] = Field(None, description="Quantity mentioned")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    context: str = Field(
        description="Context of the mention (e.g., quote_request, order)"
    )


class ProductExtractionResult(BaseModel):
    """Result of product extraction from an email"""

    products: List[ProductExtractionItem] = Field(
        default_factory=list, description="List of extracted products"
    )


llm = get_llm_client()
structured_llm = llm.with_structured_output(ProductExtractionResult)


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

    prompt = f"""
        You are analyzing business emails about industrial products and fasteners.

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
                    "properties": [{{"name": "string", "value": "string", "confidence": "test"}}],
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
        # Build prompt
        prompt = build_extraction_prompt(email)

        # Call LLM (synchronous invoke)
        try:
            response: ProductExtractionResult = structured_llm.invoke(
                [HumanMessage(content=prompt)]
            )  # type: ignore

        except json.JSONDecodeError:
            print(
                f"Warning: Failed to parse LLM response as JSON for {email.file_path}"
            )
            return []

        # Convert to ProductMention objects
        products = []
        for product in response.products:
            try:
                # Create ProductMention with email metadata
                mention = ProductMention(
                    **product.model_dump(),
                    date_requested=None,  # TODO: Parse dates from email
                    email_subject=email.metadata.subject,
                    email_sender=email.metadata.sender,
                    email_date=email.metadata.date,
                    email_file=email.file_path,
                )

                products.append(mention)
            except Exception as e:
                print(f"Warning: Failed to create ProductMention from {product}: {e}")
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

    for email in tqdm(emails, desc="Extracting products from emails"):
        products = extract_products_from_email(email)
        all_products.extend(products)

    return all_products
