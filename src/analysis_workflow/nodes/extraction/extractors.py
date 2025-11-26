"""LLM-based product extraction from emails"""

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List

from langchain_core.messages import HumanMessage
from tqdm import tqdm

from src.config.config_loader import format_config, load_config
from src.llm.client import get_llm_client
from src.models.email import Email
from src.models.product import (
    ProductExtractionResult,
    ProductMention,
)
from src.utils.property_enrichment import enrich_properties_with_metadata

structured_llm = get_llm_client(output_structure=ProductExtractionResult)


def build_extraction_prompt(email: Email) -> str:
    """
    Build the prompt for product extraction.

    Args:
        email: Email to extract products from

    Returns:
        Formatted prompt string
    """
    products_section = format_config(load_config())

    # Use cleaned body if available, otherwise raw body
    email_content = email.cleaned_body if email.cleaned_body else email.body

    prompt = f"""
        You are analyzing business emails about industrial products.

        Extract every individual product mention separately. If the product is mentioned multiple times with variations, explicitly identify each mention separately, even if they refer to the same product type with different properties or quantities.

        Extract all product mentions from the email below. The following details should be identified for each product:
        0. A comprehensive free text snippet from the email that identified the product. Include any surrounding context that that helps identify the product. Focus on the extracting product details accurately. This should only contain the details of a single product with a single combination of properties, quantity, and unit.
        1. The category of product (using the supplied definitions) extracted from the free text snippet. If it is not clear, use "Unknown".
        2. The name of the product extracted from the free text snippet. If it is not clear, use "Unknown".
        3. A list of properties with name, value, and confidence score. Set the value_type to "<unknown>" as this will be added automatically from the config. If no properties are mentioned, return an empty list. If there are multiple values for a property, combine them into a single value separated by "/".
        4. Quantity if mentioned extracted from the free text snippet.
        5. Unit of measurement if mentioned extracted from the free text snippet.
        6. Context explaining the intent of the message from the overall email (quote_request, order, inquiry, pricing_request, etc.).
        7. Identify who is requesting the product in the 'requestor' attribute. This should be identifiable from the email content where the email address of the person is labelled "From" or similar above the content. Use the email sender's address if present and ONLY use the email. If this is not available then use other relevant information available in the email that indicates the requestor.

        Examples of requestor identification:
        Example 1:
        From: Scott Patrick <scottp@nutsupply.com>
        Sent: Monday, November 3, 2025 2:31 PM
        To: Dan Manspan <sales@eastbrand.ca>
        Subject: Price and availability

        Requestor = scottp@nutsupply.com

        Example 2:
        From: Dan Manspan </O=EXCHANGELABS/OU=EXCHANGE ADMINISTRATIVE GROUP (FYIBOHF23SPDT)/CN=RECIPIENTS/CN=893ED34062DB489F89D236F6EA0D88C4-BB00E497-2E>
        To: Scott Patrick <scottp@nutsupply.com>

        Requestor = Dan Manspan

        However if Example 1 and 2 are in the same email chain, and the requestor is identified as "Dan Manspan", reason that the email address for "From" in a previous email connected "Dan Manspan" to the email address "sales@eastbrand.ca" and use that as the requestor.

        8. The date the product was requested if mentioned in the free text snippet. This is identifiable from the email metadata which often includes a datetime stamp of when the email was sent.

        Follow the below output structure:
        {{
            "products": [
                {{
                    "exact_product_text": "string",
                    "product_category": "string",
                    "product_name": "string",
                    "properties": [
                        {{
                            "name": "string", 
                            "value": "string", 
                            "confidence": "float (0.0 to 1.0)"
                        }}
                    ] as List[ProductProperty],
                    "quantity": number or null,
                    "unit": "string or null",
                    "context": "QuoteContext or string",
                    "requestor": "string",
                    "date_requested": "string (format as yyyy-MM-dd and if time is available include HH:mm:ss) or null"
                }}
            ]
        }}

        If no products are found, return {{"products": []}}.

        Below are the key product types to search for in the emails. They include examples of the product configurations which should help identify relevant products in the email. Do not use these values directly, only use them to guide extraction.

        PRODUCT DEFINITIONS:
        {products_section}

        Below is the email to extract products from:
        EMAIL SUBJECT: 
        {email.metadata.subject}
        EMAIL BODY:
        {email_content}
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

        except Exception as e:
            print(f"Error {email.file_path}: {e}")
            return []

        # Convert to ProductMention objects
        products = []
        for product in response.products:
            try:
                # Enrich properties with value_type and priority from config
                enriched_properties = enrich_properties_with_metadata(
                    product.properties,
                    product.product_category,
                )

                # Create ProductMention with enriched properties and email metadata
                product_dict = product.model_dump()
                product_dict["properties"] = enriched_properties

                mention = ProductMention(
                    **product_dict,
                    email_subject=email.metadata.subject,
                    email_sender=email.metadata.sender,
                    email_file=email.file_path,
                    thread_hash=email.thread_hash,
                )

                products.append(mention)
            except Exception as e:
                print(f"Warning: Failed to create ProductMention from {product}: {e}")
                continue

        # Deduplicate AI-generated product mentions
        deduplicated_products = deduplicate_ai_product_mentions(products)

        return deduplicated_products

    except Exception as e:
        print(f"Error extracting products from email {email.file_path}: {e}")
        return []


def deduplicate_ai_product_mentions(
    products: List[ProductMention],
) -> List[ProductMention]:
    """
    Deduplicate product mentions based on properties, requestor, and quantity. This is specifically to remove duplicates generated by the AI NOT actual duplicate mentions in the email. There is uncontrollable variability in the AI output which can lead to the same product being extracted multiple times with identical attributes.

    Two products are considered duplicates if they have:
    - Same product name and category
    - Same set of properties (name-value pairs)
    - Same requestor
    - Same quantity and unit

    Args:
        products: List of ProductMention objects to deduplicate

    Returns:
        Deduplicated list of ProductMention objects
    """
    seen = set()
    deduplicated = []

    for product in products:
        # Create a hashable key from:
        # 1. Product name and category
        # 2. Sorted properties (name-value pairs)
        # 3. Requestor
        # 4. Quantity and unit

        # Sort properties to ensure consistent comparison
        sorted_props = tuple(
            sorted(
                [(prop.name, prop.value) for prop in product.properties],
                key=lambda x: (x[0], x[1]),
            )
        )

        # Create deduplication key
        dedup_key = (
            product.product_category,
            sorted_props,
            product.requestor,
            product.quantity,
            product.unit,
            product.context,
        )

        # Only add if not seen before
        if dedup_key not in seen:
            seen.add(dedup_key)
            deduplicated.append(product)
        else:
            logging.debug(f"Duplicate product mention found and removed: {product}")

    return deduplicated


def extract_products_batch(emails: List[Email]) -> List[ProductMention]:
    """
    Extract products from multiple emails.

    Args:
        emails: List of emails to process

    Returns:
        List of all ProductMention objects from all emails (deduplicated)
    """
    all_products = []

    """
    for email in tqdm(emails, desc="Extracting products from emails"):
        products = extract_products_from_email(email)
        all_products.extend(products)
    """

    with ThreadPoolExecutor(max_workers=50) as executor:
        # Submit all tasks
        future_to_task = {executor.submit(extract_products_from_email, email) for email in emails}

        for future in tqdm(future_to_task, desc="Processing parameters"):
            result = future.result()
            all_products.extend(result)

    return all_products
