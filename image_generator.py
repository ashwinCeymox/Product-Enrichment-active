"""
Image Generator — OpenRouter API integration for Gemini image generation.

Takes a reference product image URL + a text prompt, calls Gemini via OpenRouter,
and returns the generated image as base64 data.

Handles ALL known response formats from OpenRouter/Gemini:
  - OpenAI style (image_url)
  - Gemini native (inline_data)
  - Base64 JSON (b64_json)
  - Direct base64 in text
"""

import json
import re
import base64
import requests
import config


class ImageGenerator:
    """Generates images via OpenRouter using Gemini with reference image support."""

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or config.OPENROUTER_API_KEY
        self.model = model or config.IMAGE_GEN_MODEL
        self.base_url = config.OPENROUTER_BASE_URL

    def generate(self, reference_image_url: str, prompt: str) -> dict:
        """
        Generate an image using a reference image and text prompt.

        Args:
            reference_image_url: URL of the product reference image.
            prompt: The image generation prompt (from prompt_agent).

        Returns:
            dict with keys:
              - success (bool)
              - image_data (str): base64 image data (or empty on failure)
              - mime_type (str): e.g. "image/png"
              - response_text (str): any text in the response
              - error (str): error message if failed
        """
        if not prompt:
            return self._error_result("No prompt provided")

        if not self.api_key:
            return self._error_result("No OpenRouter API key configured")

        # ── Build message content ──
        content = []

        if reference_image_url:
            content.append({
                "type": "image_url",
                "image_url": {"url": reference_image_url},
            })

        content.append({
            "type": "text",
            "text": prompt,
        })

        # ── Call OpenRouter API ──
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": content,
                }
            ],
        }

        try:
            print(f"[ImageGen] Calling {self.model}...")
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=120,  # image gen can take a while
            )
            response.raise_for_status()
            api_response = response.json()

        except requests.exceptions.Timeout:
            return self._error_result("API call timed out (120s)")
        except requests.exceptions.RequestException as e:
            return self._error_result(f"API call failed: {e}")
        except json.JSONDecodeError:
            return self._error_result("Failed to parse API response as JSON")

        # ── Check for API-level errors ──
        if "error" in api_response:
            err_msg = api_response["error"]
            if isinstance(err_msg, dict):
                err_msg = err_msg.get("message", json.dumps(err_msg))
            return self._error_result(f"API error: {err_msg}")

        # ── Extract images from response ──
        return self._extract_images(api_response)

    def _extract_images(self, api_response: dict) -> dict:
        """
        Extract image data from the API response.
        Handles ALL known response formats from OpenRouter/Gemini.
        """
        choices = api_response.get("choices", [])
        images = []
        response_text = ""

        for choice in choices:
            message = choice.get("message", {})
            msg_content = message.get("content")

            if isinstance(msg_content, str):
                response_text = msg_content

                # Check for inline base64 data URIs
                base64_matches = re.findall(
                    r"data:image/[a-zA-Z]+;base64,[A-Za-z0-9+/=]+",
                    msg_content
                )
                for match in base64_matches:
                    mime, data = self._parse_data_uri(match)
                    images.append({"data": data, "mime_type": mime})

            elif isinstance(msg_content, list):
                for part in msg_content:
                    part_type = part.get("type", "")

                    # Format 1: OpenAI style — { type: "image_url", image_url: { url } }
                    if part_type == "image_url" and "image_url" in part:
                        url = part["image_url"].get("url", "")
                        if url.startswith("data:"):
                            mime, data = self._parse_data_uri(url)
                            images.append({"data": data, "mime_type": mime})
                        else:
                            # Direct URL — would need download, store URL for now
                            images.append({"data": url, "mime_type": "url"})

                    # Format 2: Simple image — { type: "image", url }
                    elif part_type == "image" and "url" in part:
                        url = part["url"]
                        if url.startswith("data:"):
                            mime, data = self._parse_data_uri(url)
                            images.append({"data": data, "mime_type": mime})

                    # Format 3: Image with nested object — { type: "image", image: { url } }
                    elif part_type == "image" and "image" in part:
                        url = part["image"].get("url", "")
                        if url.startswith("data:"):
                            mime, data = self._parse_data_uri(url)
                            images.append({"data": data, "mime_type": mime})

                    # Format 4: Gemini native — { type: "inline_data", inline_data: { mime_type, data } }
                    elif part_type == "inline_data" and "inline_data" in part:
                        mime = part["inline_data"].get("mime_type", "image/png")
                        data = part["inline_data"].get("data", "")
                        if data:
                            images.append({"data": data, "mime_type": mime})

                    # Format 5: Gemini alt — { inline_data: { mime_type, data } } (no type field)
                    elif "inline_data" in part and "data" in part.get("inline_data", {}):
                        mime = part["inline_data"].get("mime_type", "image/png")
                        data = part["inline_data"]["data"]
                        images.append({"data": data, "mime_type": mime})

                    # Format 6: Anthropic style — { type: "image", source: { type: "base64", data } }
                    elif part_type == "image" and "source" in part:
                        source = part["source"]
                        mime = source.get("media_type", "image/png")
                        data = source.get("data", "")
                        if data:
                            images.append({"data": data, "mime_type": mime})

                    # Format 7: b64_json — { b64_json: "..." }
                    elif "b64_json" in part:
                        images.append({
                            "data": part["b64_json"],
                            "mime_type": "image/png"
                        })

                    # Text parts
                    elif part_type == "text":
                        response_text += part.get("text", "")

        if not images:
            return {
                "success": False,
                "image_data": "",
                "mime_type": "",
                "response_text": response_text,
                "error": "No image found in API response",
            }

        # Return the first image (we generate one at a time)
        first_image = images[0]
        print(f"[ImageGen] SUCCESS — extracted image ({first_image['mime_type']})")

        return {
            "success": True,
            "image_data": first_image["data"],
            "mime_type": first_image["mime_type"],
            "response_text": response_text,
            "error": "",
        }

    @staticmethod
    def _parse_data_uri(data_uri: str) -> tuple:
        """Parse a data URI into (mime_type, base64_data)."""
        match = re.match(r"data:(image/[a-zA-Z]+);base64,(.+)", data_uri)
        if match:
            return match.group(1), match.group(2)
        return "image/png", data_uri

    @staticmethod
    def _error_result(message: str) -> dict:
        print(f"[ImageGen] ERROR: {message}")
        return {
            "success": False,
            "image_data": "",
            "mime_type": "",
            "response_text": "",
            "error": message,
        }
