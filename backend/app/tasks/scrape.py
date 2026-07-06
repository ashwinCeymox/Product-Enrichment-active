"""
Celery tasks for scraping and scheduled job dispatch.
"""
from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.scrape_task import ScrapeTask

from datetime import date


@celery_app.task(bind=True, name="app.tasks.scrape.process_scrape")
def process_scrape(self, task_id: str):
    """
    Phase 1: Scrape the URL, compress HTML, run AI extraction.
    Writes results to extracted_products and updates scrape_task status.
    """
    db = SessionLocal()
    try:
        task = db.query(ScrapeTask).filter(ScrapeTask.id == task_id).first()
        if not task:
            return f"Task {task_id} not found"

        # Phase 3: Web Scraping
        task.status = "scraping"
        task.progress = 30
        task.append_activity("scraping", f"Fetching HTML from {task.url}")
        db.commit()

        import httpx
        from bs4 import BeautifulSoup
        import json
        import os

        # Fetch URL
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            # Using a generic user-agent
            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/110.0"}
            response = client.get(task.url, headers=headers)
            response.raise_for_status()
            html_content = response.text

        # Compress HTML using BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove script, style, and SVG tags
        for el in soup(["script", "style", "svg", "noscript", "header", "footer", "nav"]):
            el.extract()
            
        clean_text = soup.get_text(separator=" ", strip=True)
        
        # Manually extract images so LLM can see them
        extracted_images = []
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('srcset')
            if src and not src.startswith('data:'):
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = task.url.rstrip('/') + src
                # Ignore very small or irrelevant images
                alt = img.get('alt', '')
                extracted_images.append(f"Image: {src} | Alt: {alt}")
                
        # Get unique images keeping order
        seen = set()
        unique_images = []
        for img_str in extracted_images:
            if img_str not in seen:
                seen.add(img_str)
                unique_images.append(img_str)
                
        images_context = "\\n".join(unique_images[:20]) # Limit to top 20 images

        task.status = "ai_processing"
        task.progress = 60
        task.append_activity("ai_processing", "HTML compressed, running extraction")
        db.commit()

        # Try to extract via meta tags for fallback/mock
        title = soup.find("meta", property="og:title")
        description = soup.find("meta", property="og:description")
        image = soup.find("meta", property="og:image")
        
        title_val = title["content"] if title else soup.title.string if soup.title else "Unknown Product"
        desc_val = description["content"] if description else clean_text[:200] + "..."
        img_val = image["content"] if image else ""

        # Here we call Litellm + DeepSeek + Serper
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        serper_key = os.getenv("SERPER_API_KEY")
        
        product_data = {}
        if deepseek_key and deepseek_key.strip():
            from litellm import completion
            
            task.append_activity("ai_processing", "Extracting initial product details")
            db.commit()
            
            prompt1 = f"Extract the primary product name and brand from this text.\\n\\n{clean_text[:5000]}\\n\\nFormat exactly as JSON: {{\"product_name\": \"...\"}}"
            try:
                ai_resp1 = completion(
                    model="deepseek/deepseek-chat",
                    messages=[{"role": "user", "content": prompt1}],
                    api_key=deepseek_key,
                    response_format={"type": "json_object"}
                )
                base_info = json.loads(ai_resp1.choices[0].message.content)
                product_name = base_info.get("product_name", title_val)
                
                serper_data = ""
                if serper_key and serper_key.strip() and product_name:
                    task.append_activity("ai_processing", f"Querying Serper for '{product_name}'")
                    db.commit()
                    try:
                        serper_resp = httpx.post(
                            "https://google.serper.dev/search",
                            headers={"X-API-KEY": serper_key, "Content-Type": "application/json"},
                            json={"q": f"{product_name} specifications details"}
                        )
                        serper_resp.raise_for_status()
                        serper_data = json.dumps(serper_resp.json().get("organic", [])[:3])
                    except Exception as se:
                        print(f"Serper error: {se}")

                # Read the user's detailed system prompt
                system_prompt_path = os.path.join(os.path.dirname(__file__), "../../../src/system_prompt.txt")
                try:
                    with open(system_prompt_path, "r", encoding="utf-8") as f:
                        system_prompt_text = f.read()
                except Exception as e:
                    print(f"Could not load system_prompt.txt: {e}")
                    system_prompt_text = "You are a product enrichment agent."

                task.append_activity("ai_processing", "Finalizing JSON with DeepSeek agent using detailed schema")
                db.commit()
                
                # We provide the HTML and the Serper context.
                # The system prompt dictates exactly how to merge and output.
                prompt2 = f"Source HTML Text: {clean_text[:10000]}\\n\\nFound Images:\\n{images_context}\\n\\nExtra Search Context (Serper): {serper_data}\\n\\nPerform Phase 1, Phase 5, Phase 6, and output the final JSON exactly as specified in the OUTPUT FORMAT."
                
                ai_resp2 = completion(
                    model="deepseek/deepseek-chat",
                    messages=[
                        {"role": "system", "content": system_prompt_text},
                        {"role": "user", "content": prompt2}
                    ],
                    api_key=deepseek_key,
                    response_format={"type": "json_object"}
                )
                product_data = json.loads(ai_resp2.choices[0].message.content)
                # Ensure images list is populated correctly
                if not product_data.get("images") and img_val:
                    product_data["images"] = [img_val]
                    
            except Exception as e:
                print(f"LLM Error: {e}")
                product_data = {
                    "title": title_val,
                    "description": desc_val,
                    "features": ["Feature 1", "Feature 2"],
                    "price": "$0.00",
                    "images": [img_val] if img_val else [],
                    "error": str(e)
                }
        else:
            # Fallback JSON
            product_data = {
                "title": title_val,
                "description": desc_val,
                "price": "$0.00",
                "features": ["Durable", "High quality"],
                "images": [img_val] if img_val else [],
                "source_url": task.url
            }

        # Save to database
        task.product_data = product_data
        task.status = "waiting_for_approval"
        task.progress = 90
        task.append_activity("waiting_for_approval", "Extraction complete, awaiting admin review")
        db.commit()

        return f"Task {task_id} scrape complete → waiting_for_approval"

    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)
        task.append_activity("failed", str(e))
        db.commit()
        return f"Task {task_id} failed: {e}"
    finally:
        db.close()


@celery_app.task(name="app.tasks.scrape.dispatch_scheduled_jobs")
def dispatch_scheduled_jobs():
    """
    Celery Beat periodic task: find scrape_tasks with
    scheduled_date <= today and status='pending', dispatch them.
    """
    db = SessionLocal()
    try:
        today = date.today()
        due_tasks = (
            db.query(ScrapeTask)
            .filter(
                ScrapeTask.status == "pending",
                ScrapeTask.scheduled_date <= today,
            )
            .all()
        )

        dispatched = 0
        for task in due_tasks:
            task.status = "queued"
            task.append_activity("queued", "Dispatched by Celery Beat scheduler")
            db.commit()
            # Dispatch the actual scrape task
            process_scrape.delay(task.id)
            dispatched += 1

        return f"Dispatched {dispatched} scheduled job(s)"
    finally:
        db.close()
