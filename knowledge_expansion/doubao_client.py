# doubao_client.py
import os
import base64
import requests
import time
import logging
from PIL import Image
from io import BytesIO
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DoubaoClient:
    def __init__(self, api_base="https://ark.cn-beijing.volces.com/api/v3"):
        api_key = os.getenv("DOUBAO_API_KEY")
        if not api_key:
            raise ValueError("Please set DOUBAO_API_KEY")
        
        self.api_key = api_key
        self.api_base = api_base

        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

    def encode_image(self, image_path):
        img = Image.open(image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')

        output = BytesIO()
        img.save(output, format="JPEG", quality=95)
        output.seek(0)
        return base64.b64encode(output.getvalue()).decode("utf-8")

    def call_model(self, model_name, image_path, prompt, max_retries=3):
        base64_img = self.encode_image(image_path)
        url = f"{self.api_base}/chat/completions"

        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_img}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        }

        for attempt in range(max_retries):
            try:
                response = self.session.post(url, json=payload, headers=self.headers, timeout=30)
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            except requests.exceptions.RequestException as e:
                logger.warning(f"API call failed (try {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    return "CONNECTION_ERROR"
            except Exception as e:
                logger.error(f"Error processing response: {e}")
                return "ERROR"

