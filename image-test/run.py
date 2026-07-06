# run.py
import json
import asyncio

# Assuming these exist in your main project:
# from src.scraper import fetch_url
# from src.compressor import compress_html
# from src.orchestrator import run_agent
# from tests.schema import ProductOutput

from src.tools.image_pipeline import process_images

def main():
    url = "https://joola.com/products/joola-tyson-mcguffin-magnus-cas-14-pickleball-paddle"

    # Step 1: your existing scraper + compressor
    print(f"[run] scraping source URL...")
    
    # --- Dummy placeholders for your actual imports ---
    # raw_html     = fetch_url(url)
    # compressed   = compress_html(raw_html)
    # cleaned_html = compressed["cleanedHtml"]
    
    # print(f"[run] compressed to {compressed['compressedLengthBytes']} bytes "
    #       f"({compressed['compressionRatioPercent']} reduction)")

    # Step 2: run the agent
    # result = run_agent(cleaned_html=cleaned_html, source_url=url)
    
    # For demonstration, we load the existing test result:
    with open("joola_magnus_output.json", "r") as f:
        result = json.load(f)

    # Step 3: validate against schema
    try:
        # validated = ProductOutput(**result)
        print("\n[run] schema validation PASSED")
        # product_dict = validated.model_dump()
        product_dict = result # placeholder since we don't have ProductOutput here
        
        print("\n[run] Starting Image Generation Pipeline...")
        # Step 4: Pass the validated dictionary to the image pipeline
        enriched_product = asyncio.run(process_images(product_dict))
        
        print("\n[run] Final Enriched Product Output:")
        # print(json.dumps(enriched_product, indent=2))
        
        # Save the final result
        with open("final_product.json", "w") as f:
            json.dump(enriched_product, f, indent=2)
            
        print("\n[run] Pipeline completed successfully!")

    except Exception as e:
        print(f"\n[run] schema validation FAILED: {e}")
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
