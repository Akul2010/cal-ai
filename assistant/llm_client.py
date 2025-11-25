import os
from ctransformers import AutoModelForCausalLM

# Default model settings for Raspberry Pi / Low-end devices
DEFAULT_MODEL_REPO = "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF"
DEFAULT_MODEL_FILE = "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"

class LLMClient:
    def __init__(self, model_path=None):
        self.model_path = model_path
        self.model = None
        self._ensure_model()
        self._load_model()

    def _ensure_model(self):
        """
        Ensure the model file exists. If not, download it.
        """
        if self.model_path and os.path.exists(self.model_path):
            return

        # Define a default storage location if no path provided
        if not self.model_path:
            base_dir = os.path.join(os.getcwd(), "cal_ai", "models")
            os.makedirs(base_dir, exist_ok=True)
            self.model_path = os.path.join(base_dir, DEFAULT_MODEL_FILE)

        if os.path.exists(self.model_path):
            return

        print(f"[CAL][LLM] Model not found at {self.model_path}. Downloading...")
        try:
            from huggingface_hub import hf_hub_download
            # Download to the specific path
            hf_hub_download(
                repo_id=DEFAULT_MODEL_REPO,
                filename=DEFAULT_MODEL_FILE,
                local_dir=os.path.dirname(self.model_path),
                local_dir_use_symlinks=False
            )
            print(f"[CAL][LLM] Download complete: {self.model_path}")
        except ImportError:
            print("[CAL][LLM] Error: huggingface_hub not installed. Cannot download model automatically.")
            print("Please install it or manually place the model file.")
        except Exception as e:
            print(f"[CAL][LLM] Download failed: {e}")

    def _load_model(self):
        if not os.path.exists(self.model_path):
            print("[CAL][LLM] No model file available. LLM features disabled.")
            return

        try:
            # Set threads to a reasonable default for Pi (e.g., 4)
            # context_length=2048 is standard for TinyLlama
            self.model = AutoModelForCausalLM.from_pretrained(
                os.path.abspath(self.model_path),
                model_type="llama",
                context_length=2048,
                threads=4
            )
            print(f"[CAL][LLM] Loaded model from {self.model_path}")
        except Exception as e:
            print(f"[CAL][LLM] Failed to load model: {e}")
            self.model = None

    def generate(self, prompt, max_new_tokens=128, temperature=0.7, stop=None):
        if not self.model:
            return None
        
        try:
            # TinyLlama chat template format:
            # <|system|>\n{system_prompt}</s>\n<|user|>\n{user_prompt}</s>\n<|assistant|>
            # We'll assume the caller handles the formatting or we do simple raw generation.
            # For now, let's just pass the prompt through.
            return self.model(
                prompt,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                stop=stop or []
            )
        except Exception as e:
            print(f"[CAL][LLM] Generation error: {e}")
            return None
